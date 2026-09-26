# Tasks: 메르카리 키워드 신착 알림기 (1단계)

**Input**: Design documents from `/specs/001-keyword-alarm/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: constitution VI에 따라 분기 로직(새 상품 판정, 묶음, 고장 감지, 키워드 검증)은 `unittest`를 둔다.
네트워크 호출(메르카리·ntfy)은 테스트하지 않고 quickstart 수동 점검으로 확인한다.

**Organization**: 사용자 스토리별. 모든 경로는 저장소 루트 기준.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 다른 파일이고 미완료 작업에 의존하지 않아 병렬 가능
- **[Story]**: US1(새 상품 알림), US2(키워드 관리 화면), US3(고장 감지)

---

## Phase 1: Setup

- [X] T001 [P] `requirements.txt` 생성: `cryptography` 한 줄 (research R3)
- [X] T002 [P] `.env.example` 생성: `NTFY_TOPIC=`, `NTFY_SERVER=https://ntfy.sh`, `PORT=8787` (주석으로 토픽은 무작위 문자열)
- [X] T003 [P] `.gitignore`에 `keywords.txt`, `state.json`, `alarm.log*`, `__pycache__/` 추가 (기존 `.env` 항목 유지)

---

## Phase 2: Foundational (모든 스토리의 전제)

- [X] T004 `alarm.py` 뼈대: `.env` 로더(표준 라이브러리, `KEY=VALUE` 줄 파싱, 없으면 환경변수), 설정 상수
  (`INTERVAL=60`, `GAP=2`, `MAX_KEYWORDS=20`, `MAX_LEN=50`, `SEEN_LIMIT=500`, `BURST=5`, `FAIL_ALERT_SEC=600`, `CLOCK_SLACK=60`),
  `logging` + `RotatingFileHandler("alarm.log", 1MB × 3)`, 경로는 `pathlib`으로 스크립트 폴더 기준
- [X] T005 `alarm.py`에 파일 입출력: `load_keywords()`(UTF-8, 공백 제거, 빈 줄 무시, 규칙 위반 줄은 로그 경고 후 제외),
  `save_keywords(list)`, `load_state()`/`save_state(dict)` — 쓰기는 임시 파일 + `os.replace`, 모듈 전역 `threading.Lock` 하나로 보호
  ([data-model.md](./data-model.md))
- [X] T006a `alarm.py`에 `translate(text) -> str | None`: research R4a 주소, 타임아웃 5초, 모든 예외는 로그 후 `None`
- [X] T006 `alarm.py`에 `notify(title, message, click=None)`: `POST {NTFY_SERVER}/`에 JSON `{topic,title,message,click}`,
  `urllib.request`, 타임아웃 10초, 실패 시 예외 (research R4)

**Checkpoint**: 설정·파일·푸시 함수 준비 완료

---

## Phase 3: User Story 1 — 새 상품 푸시 알림 받기 (Priority: P1) 🎯 MVP

**Goal**: `keywords.txt`에 적힌 키워드의 새 상품을 1분 주기로 폰에 푸시.

**Independent Test**: `keywords.txt`에 넓은 키워드 하나를 넣고 `py alarm.py` 실행 → 첫 조회 무알림, 이후 새 상품 푸시, 누르면 상품 페이지 (quickstart §3).

### Tests for User Story 1

- [X] T007 [P] [US1] `test_alarm.py`에 `decide()` 테스트: (a) state 없음 → 알림 0, 전체 `seen` 등록·`since=now`,
  (b) 미확인 + `created ≥ since-60` → 알림, (c) 미확인 + `created < since-60` → 알림 없이 `old_bump`,
  (d) 이미 `seen` → 무시, (e) 새 상품 8개 → 개별 5 + `overflow=3`, 순서는 목록 순서 유지, (f) 결과 전부 미확인이면 포화 플래그 True, (g) `item_message()`: 번역 있으면 `번역\n¥12,800\n(원문)`, `None`이면 `원문\n¥12,800`, 가격은 천 단위 쉼표

### Implementation for User Story 1

- [X] T008 [P] [US1] `mercari.py`: `Item` (dataclass: `id,name,price:int,created:int,shops:bool,url`),
  모듈 로드 시 P-256 키 1회 생성, `_dpop(url)` ES256 JWT, `search(keyword) -> list[Item]` —
  `POST https://api.mercari.jp/v2/entities:search`, 본문·헤더는 research R1 그대로(`pageSize:120`, `SORT_CREATED_TIME`,
  `ORDER_DESC`, `STATUS_ON_SALE`, 두 데이터셋), 타임아웃 15초, 실패·형식 이상은 예외,
  Shops(`ITEM_TYPE_BEYOND`)는 `https://jp.mercari.com/shops/product/<id>` ([contracts/mercari-search.md](./contracts/mercari-search.md))
- [X] T009 [US1] `alarm.py`에 `decide(state, items, now) -> (state, fresh, saturated)` 순수 함수 (개별 5/묶음 분할은 `fresh[:BURST]`로 호출 쪽에서) (data-model "새 상품 판정 규칙"), T007 통과
- [X] T010 [US1] `alarm.py`에 `run_cycle()`: 키워드마다 `search` → `decide` → 개별 상품마다 `translate(name)` → `item_message()`로 본문 조립 → `notify`(click=상품 URL)
  → `overflow>0`이면 묶음 `notify`(click=키워드 검색 URL, data-model 표) → 전송 성공분 + `old_bump`만 `seen`에 추가,
  `SEEN_LIMIT` 초과분 앞에서 제거, 조회 결과 120개가 **전부** 미확인이면(창 포화 = 놓친 상품이 있을 수 있음) 로그에 경고(constitution IV), 키워드 사이 `GAP`초, **키워드별 try/except**로 실패는 로그만(FR-019),
  `keywords.txt`에 없는 키워드의 state 삭제(FR-015), 끝나면 `save_state`
- [X] T011 [US1] `alarm.py`에 `main()`: 설정 로드(토픽 없으면 로그 후 종료), 조회 루프(주기 시작 기준 `INTERVAL`마다 `run_cycle`,
  루프 전체 예외도 잡아 로그 후 계속), `if __name__ == "__main__"`

**Checkpoint**: US1 단독 동작 — 키워드는 메모장으로 관리

---

## Phase 4: User Story 2 — 폰에서 키워드 보기·추가·삭제 (Priority: P2)

**Goal**: 폰 홈 화면 아이콘으로 키워드 목록·추가·삭제.

**Independent Test**: quickstart §3 "관리 화면~입력 검증" 행, §4 홈 화면 추가.

### Tests for User Story 2

- [X] T012 [P] [US2] `test_alarm.py`에 `validate_keyword()` 테스트: 앞뒤 공백 제거, 빈 값·51자 → `ValueError`,
  정확히 같은 문자열 중복 → `ValueError`, 전각/반각 다르면 허용, 21번째 → `ValueError`, 오류 메시지는 contracts/web-api.md 문구

### Implementation for User Story 2

- [X] T013 [US2] `alarm.py`에 `validate_keyword(raw, existing) -> str`, `add_keyword(raw)`, `remove_keyword(k)`
  (삭제 시 state에서도 제거) — 둘 다 Lock 안에서 파일 갱신, T012 통과
- [X] T014 [US2] `alarm.py`의 `Handler`(구현 중 `web.py`에서 합침, plan 참조): `ThreadingHTTPServer` 핸들러 — `GET /`·`/manifest.json`·`/icon.png`는 `static/`에서 제공
  (화이트리스트, 경로 조작 불가), `GET/POST/DELETE /api/keywords`는 [contracts/web-api.md](./contracts/web-api.md) 상태코드·문구 그대로,
  POST는 `Content-Type: application/json` 아니면 415, 요청 본문 최대 4KB, CORS 헤더 없음, 요청 로그는 `logging`으로
- [X] T015 [P] [US2] `static/index.html`: 목록(각 항목 삭제 버튼)·입력창·추가 버튼·오류 영역, 인라인 CSS/JS, `fetch`로 API 호출,
  키워드는 `textContent`로만 렌더(FR-013), 360px 폭 가로 스크롤 없음, 터치 영역 44px+, `<link rel="manifest">`,
  `apple-mobile-web-app-capable`, `apple-touch-icon`, 라이트/다크 대응
- [X] T016 [P] [US2] `static/manifest.json`(name, short_name, start_url `/`, display `standalone`, icons) + `static/icon.png`(192×192 이상 단색 종 아이콘)
- [X] T017 [US2] `alarm.py`의 `main()`에서 관리 웹 서버를 데몬 스레드로 `0.0.0.0:PORT`에 기동

**Checkpoint**: US1 + US2 동작

---

## Phase 5: User Story 3 — 알림기 고장 알아차리기 (Priority: P3)

**Goal**: 10분 연속 조회 실패 시 경고 푸시 1회, 복구 시 초기화.

**Independent Test**: quickstart §3 "고장 감지" 행.

### Tests for User Story 3

- [X] T018 [P] [US3] `test_alarm.py`에 `FailureWatch` 테스트: 시작 직후 경고 안 함, 600초 미만 경고 안 함, 600초 이상 경고,
  경고 전송 성공 후 반복 안 함, 전송 실패면 다음 주기 재시도, `ok()` 후 초기화되어 다시 600초 뒤 경고

### Implementation for User Story 3

- [X] T019 [US3] `alarm.py`에 `FailureWatch`(`last_success`, `alerted`; `ok(now)`, `should_alert(now)`, `mark_alerted()`), T018 통과
- [X] T020 [US3] `run_cycle()`/루프에 연결: 키워드 조회가 하나라도 성공하거나 키워드 0개면 `ok(now)`, 주기 끝에 `should_alert`면
  경고 `notify`("알림기 조회 실패 중", "N분째 메르카리 조회가 실패하고 있습니다. alarm.log를 확인하세요.") 성공 시 `mark_alerted()`

**Checkpoint**: 모든 스토리 동작

---

## Phase 6: Polish & Cross-Cutting

- [X] T021 [P] `README.md`에 한 문단 소개 + quickstart 링크(`specs/001-keyword-alarm/quickstart.md`)와 "넓은 키워드는 놓칠 수 있음" 주의
- [X] T022 `py -m unittest -v` 전체 통과 확인
- [X] T023 macOS에서 수동 스모크: 임시 `.env`(테스트 토픽)로 `python3 alarm.py` 실행, 관리 화면에서 키워드 추가 → 첫 조회 무알림 →
  ntfy 수신 확인 (quickstart §3 일부). Windows 전용 단계(§5 작업 스케줄러)는 사용자가 PC에서 수행

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → US1 → US2 → US3 → Polish
- US2는 US1의 파일 함수(T005)만 필요하지만, 단일 `alarm.py`를 함께 고치므로 순서대로 진행
- US3는 `run_cycle`(T010)에 연결하므로 US1 이후
- 같은 스토리 안: 테스트 → 순수 함수 → 연결

### Parallel Opportunities

- T001, T002, T003 동시
- US1: T007(테스트)과 T008(`mercari.py`) 동시
- US2: T012, T015, T016 동시 (T013 → T014 → T017은 순서대로)
- US3: T018 먼저, 이어서 T019 → T020

## Implementation Strategy

- **MVP = Phase 1~3 (US1)**: 메모장으로 키워드를 넣고 폰으로 알림을 받는 상태. 여기서 한 번 멈춰 실제 알림을 확인한다.
- 이어서 US2(관리 화면), US3(고장 감지)를 붙인다. 각 단계 끝의 Checkpoint에서 quickstart 해당 행으로 확인.
- 기능 브랜치 `001-keyword-alarm` → `develop` PR, 리뷰 CI 확인 후 사용자 머지 (constitution 개발 워크플로).
