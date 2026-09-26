"""메르카리 키워드 신착 알림기 (1단계). 설계: specs/001-keyword-alarm/

한 프로세스에 두 스레드: 1분마다 메르카리를 조회해 ntfy로 푸시하는 루프 + 키워드 관리 웹 서버.
실행: py alarm.py  (상시 실행은 quickstart §5의 작업 스케줄러)
"""
import ipaddress
import json
import logging
import os
import sys
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from logging.handlers import RotatingFileHandler
from pathlib import Path

import mercari

BASE = Path(__file__).resolve().parent
KEYWORDS_FILE = BASE / "keywords.txt"
STATE_FILE = BASE / "state.json"
STATIC_DIR = BASE / "static"

INTERVAL = 60          # 조회 주기(초)
GAP = 2                # 키워드 사이 간격(초)
MAX_KEYWORDS = 20
MAX_LEN = 50
SEEN_LIMIT = 500       # 키워드당 기억하는 상품 ID 수 (조회 120개의 4배 이상)
BURST = 5              # 키워드당 개별 알림 상한, 나머지는 "외 N건"
FAIL_ALERT_SEC = 600   # 연속 실패 경고 기준
CLOCK_SLACK = 60       # PC·메르카리 시계 차이 여유(초)

log = logging.getLogger("alarm")
_warned = set()  # keywords.txt 무시 경고는 줄마다 한 번만 (매분 반복 방지)
# ponytail: 파일 두 개를 전역 락 하나로 보호. 요청이 분당 몇 번이라 충분하다.
lock = threading.Lock()


# ---------- 설정·파일 ----------

def load_env(path=BASE / ".env"):
    """KEY=VALUE 줄을 환경변수로. 이미 있는 환경변수가 우선."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        key, sep, value = line.partition("=")
        if sep and not key.strip().startswith("#"):
            os.environ.setdefault(key.strip(), value.strip())


def _write(path, text):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)  # 원자적 교체: 쓰다 죽어도 반쪽 파일이 남지 않는다


def validate_keyword(raw, existing):
    k = raw.strip()
    if not 1 <= len(k) <= MAX_LEN:
        raise ValueError(f"키워드는 1~{MAX_LEN}자여야 합니다")
    if k.splitlines() != [k]:  # 줄바꿈이 섞이면 keywords.txt에서 여러 키워드로 쪼개진다
        raise ValueError("키워드에 줄바꿈을 넣을 수 없습니다")
    if k in existing:
        raise ValueError("이미 등록된 키워드입니다")
    if len(existing) >= MAX_KEYWORDS:
        raise ValueError(f"키워드는 최대 {MAX_KEYWORDS}개까지 등록할 수 있습니다")
    return k


def load_keywords():
    try:
        # utf-8-sig: 메모장이 붙이는 BOM 제거
        lines = KEYWORDS_FILE.read_text(encoding="utf-8-sig").splitlines()
    except FileNotFoundError:
        return []
    keywords = []
    for line in lines:
        if not line.strip():
            continue
        try:
            keywords.append(validate_keyword(line, keywords))
        except ValueError as e:
            if line not in _warned:
                _warned.add(line)
                log.warning("keywords.txt 줄 무시 %r: %s", line, e)
    return keywords


def save_keywords(keywords):
    _write(KEYWORDS_FILE, "".join(k + "\n" for k in keywords))


def load_state():
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def save_state(state):
    _write(STATE_FILE, json.dumps(state, ensure_ascii=False, indent=1))


def add_keyword(raw):
    with lock:
        keywords = load_keywords()
        keywords.append(validate_keyword(raw, keywords))
        save_keywords(keywords)
        return keywords


def remove_keyword(keyword):
    with lock:
        keywords = load_keywords()
        if keyword not in keywords:
            raise KeyError(keyword)
        keywords.remove(keyword)
        save_keywords(keywords)
        state = load_state()
        if state.pop(keyword, None) is not None:
            save_state(state)
        return keywords


# ---------- 판정 ----------

def decide(state, items, now):
    """새 상품 판정 → (새 state, 알릴 상품, 조회 창 포화 여부). data-model.md "새 상품 판정 규칙"."""
    if state is None:  # 첫 조회: 이미 있던 상품은 알리지 않고 기억만
        return {"since": now, "seen": [i.id for i in items][-SEEN_LIMIT:]}, [], False
    seen = set(state["seen"])
    fresh, known = [], []
    for i in items:
        # 신상품순은 실제로 "최근 수정순"이라 가격 수정된 옛 상품도 올라온다 → 등록 시각으로 거른다
        if i.id not in seen and i.created >= state["since"] - CLOCK_SLACK:
            fresh.append(i)
        else:
            known.append(i.id)
    window = {i.id for i in items}
    # 이번 결과에 보인 ID는 뒤로 옮긴다. 앞에서부터 잘리므로, 아직 목록에 뜨는 상품을 잊어 중복 알림하는 일을 막는다
    kept = [x for x in state["seen"] if x not in window] + known
    # ponytail: 요청 120개 중 몇 개는 빠져서 온다(실측 114~118). 창이 거의 찼는데 아는 상품이 하나도 없으면 포화로 본다
    saturated = len(items) >= mercari.PAGE_SIZE - 20 and not (seen & window)
    return {"since": state["since"], "seen": kept[-SEEN_LIMIT:]}, fresh, saturated


class FailureWatch:
    """조회가 FAIL_ALERT_SEC 이상 연속 실패하면 한 번 경고, 성공하면 초기화."""

    def __init__(self, now):
        self.last_success = now
        self.alerted = False

    def ok(self, now):
        self.last_success = now
        self.alerted = False

    def should_alert(self, now):
        return not self.alerted and now - self.last_success >= FAIL_ALERT_SEC

    def mark_alerted(self):
        self.alerted = True


# ---------- 외부 호출 ----------

def translate(text):
    """일본어 → 한국어. 실패하면 None (알림은 원문으로 계속). research.md R4a."""
    url = "https://translate.googleapis.com/translate_a/single?" + urllib.parse.urlencode(
        {"client": "gtx", "sl": "ja", "tl": "ko", "dt": "t", "q": text})
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.load(res)
        return "".join(seg[0] for seg in data[0] if seg[0]) or None
    except Exception:
        log.warning("번역 실패 %r", text, exc_info=True)
        return None


def item_message(item, translated):
    price = f"¥{item.price:,}"
    if translated and translated != item.name:
        return f"{translated}\n{price}\n({item.name})"
    return f"{item.name}\n{price}"


def search_url(keyword):
    return "https://jp.mercari.com/search?" + urllib.parse.urlencode(
        {"keyword": keyword, "sort": "created_time", "order": "desc", "status": "on_sale"})


def notify(title, message, click=None):
    body = {"topic": os.environ["NTFY_TOPIC"], "title": title, "message": message}
    if click:
        body["click"] = click
    server = os.environ.get("NTFY_SERVER") or "https://ntfy.sh"
    req = urllib.request.Request(server.rstrip("/") + "/", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=10).close()


# ---------- 조회 루프 ----------

def check_keyword(keyword, now):
    items = mercari.search(keyword)  # 실패는 예외로 호출자에게 (고장 감지)
    with lock:
        prev = load_state().get(keyword)
    state, fresh, saturated = decide(prev, items, now)
    if saturated:
        log.warning("조회 창 포화 %r: 120건이 전부 처음 보는 상품이라 놓친 상품이 있을 수 있음", keyword)

    sent = []
    for it in fresh[:BURST]:
        try:
            notify(keyword, item_message(it, translate(it.name)), it.url)
            sent.append(it.id)
        except Exception:
            log.exception("알림 실패 %r %s", keyword, it.id)  # seen에 안 넣음 → 다음 주기 재시도
    rest = fresh[BURST:]
    if rest:
        try:
            notify(keyword, f"외 {len(rest)}건의 새 상품", search_url(keyword))
            sent += [i.id for i in rest]
        except Exception:
            log.exception("묶음 알림 실패 %r", keyword)
    if fresh:
        log.info("%r 새 상품 %d건, 알림 성공 %d건", keyword, len(fresh), len(sent))

    state["seen"] = (state["seen"] + sent)[-SEEN_LIMIT:]
    if state == prev:
        return  # 바뀐 게 없으면 쓰지 않는다
    with lock:
        all_state = load_state()
        # 조회·알림 중에 삭제(또는 삭제 후 재등록)됐으면 옛 state로 덮어쓰지 않는다 → 다음 주기에 새로 시작
        if keyword not in load_keywords() or all_state.get(keyword) != prev:
            return
        all_state[keyword] = state
        save_state(all_state)


def run_cycle(watch):
    with lock:
        keywords = load_keywords()
        state = load_state()
        if set(state) - set(keywords):  # 메모장으로 지운 키워드의 기억 정리
            save_state({k: v for k, v in state.items() if k in keywords})
    if not keywords:
        watch.ok(time.time())
    for n, keyword in enumerate(keywords):
        if n:
            time.sleep(GAP)
        try:
            check_keyword(keyword, int(time.time()))
            watch.ok(time.time())
        except Exception:
            log.exception("조회 실패 %r", keyword)  # 다른 키워드는 계속
    if watch.should_alert(time.time()):
        minutes = int((time.time() - watch.last_success) // 60)
        try:
            notify("알림기 조회 실패 중", f"{minutes}분째 메르카리 조회가 실패하고 있습니다. alarm.log를 확인하세요.")
            watch.mark_alerted()
        except Exception:
            log.exception("경고 알림 실패 (다음 주기에 재시도)")


# ---------- 관리 웹 ----------

STATIC = {"/": ("index.html", "text/html; charset=utf-8"),
          "/manifest.json": ("manifest.json", "application/manifest+json"),
          "/icon.png": ("icon.png", "image/png")}


def host_allowed(host_header):
    """DNS 리바인딩 차단: IP·localhost·점 없는 PC 이름·Tailscale(*.ts.net)만 허용."""
    if "@" in host_header:  # "evil.com@localhost" 같은 값이 localhost로 해석되는 것 차단
        return False
    try:
        host = urllib.parse.urlsplit("//" + host_header).hostname  # 포트·[IPv6] 괄호 제거, 소문자화
    except ValueError:
        return False
    if not host:
        return False
    if "." not in host or host.endswith(".ts.net"):
        return True
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body=b"", ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode())

    def _route(self):
        """허용된 Host면 경로를 돌려주고, 아니면 403을 보내고 None."""
        if not host_allowed(self.headers.get("Host", "")):
            self._send(403)
            return None
        return urllib.parse.urlsplit(self.path)

    def do_GET(self):
        url = self._route()
        if url is None:
            return
        if url.path == "/api/keywords":
            with lock:
                keywords = load_keywords()
            return self._json(200, {"keywords": keywords})
        if url.path in STATIC:
            name, ctype = STATIC[url.path]
            return self._send(200, (STATIC_DIR / name).read_bytes(), ctype)
        self._send(404)

    def do_POST(self):
        url = self._route()
        if url is None:
            return
        if url.path != "/api/keywords":
            return self._send(404)
        # JSON만 받는다: 다른 사이트의 폼 요청은 CORS preflight가 필요해 여기까지 못 온다
        if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            return self._send(415)
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if not 0 <= length <= 4096:
                return self._send(413)
            keyword = json.loads(self.rfile.read(length))["keyword"]
            if not isinstance(keyword, str):
                raise TypeError
        except (ValueError, KeyError, TypeError):
            return self._json(400, {"error": "잘못된 요청입니다"})
        try:
            return self._json(201, {"keywords": add_keyword(keyword)})
        except ValueError as e:
            return self._json(400, {"error": str(e)})

    def do_DELETE(self):
        url = self._route()
        if url is None:
            return
        if url.path != "/api/keywords":
            return self._send(404)
        keyword = urllib.parse.parse_qs(url.query).get("keyword", [""])[0]
        try:
            return self._json(200, {"keywords": remove_keyword(keyword)})
        except KeyError:
            return self._json(404, {"error": "등록되지 않은 키워드입니다"})

    def log_message(self, fmt, *args):
        log.info("web %s " + fmt, self.client_address[0], *args)


# ---------- 진입점 ----------

def main():
    load_env()
    handlers = [RotatingFileHandler(BASE / "alarm.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")]
    if sys.stderr:  # pythonw에는 콘솔이 없다
        handlers.append(logging.StreamHandler())
    logging.basicConfig(level=logging.INFO, handlers=handlers, format="%(asctime)s %(levelname)s %(message)s")

    if not os.environ.get("NTFY_TOPIC"):
        log.error(".env에 NTFY_TOPIC이 없습니다 (.env.example 참고)")
        return
    port = int(os.environ.get("PORT") or 8787)
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)  # 포트 충돌이면 여기서 죽고 로그에 남는다
    threading.Thread(target=server.serve_forever, daemon=True).start()
    log.info("시작: 관리 화면 http://localhost:%d", port)

    watch = FailureWatch(time.time())
    while True:
        started = time.monotonic()
        try:
            run_cycle(watch)
        except Exception:
            log.exception("주기 실패")
        time.sleep(max(0.0, INTERVAL - (time.monotonic() - started)))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("비정상 종료")  # 작업 스케줄러가 1분 뒤 재시작
        raise
