# Implementation Plan: 메르카리 키워드 신착 알림기 (1단계)

**Branch**: `001-keyword-alarm` | **Date**: 2026-09-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-keyword-alarm/spec.md`

## Summary

집 Windows PC에서 도는 Python 프로세스 하나. 조회 스레드가 1분마다 키워드별로 메르카리 내부 검색 API를
호출해 "키워드 등록 이후 등록된, 아직 본 적 없는" 판매 중 상품을 상품명 한국어 번역(원문 병기)과 함께 ntfy로 푸시한다. 같은 프로세스의 웹 스레드가
키워드 관리 화면(PWA)과 JSON API를 제공하고, 폰은 Tailscale로 접속한다. 10분 연속 조회 실패 시 경고 푸시.

## Technical Context

**Language/Version**: Python 3.12+ (Windows 공식 설치판; 개발은 macOS에서도 가능)

**Primary Dependencies**: `cryptography` 1개 (DPoP ES256 서명 — research R3). 나머지는 표준 라이브러리
(`urllib.request`, `http.server`, `threading`, `json`, `logging`, `unittest`)

**Storage**: 파일 — `keywords.txt`, `state.json` (원자적 교체 쓰기), `.env`, `alarm.log`

**Testing**: `unittest` (`py -m unittest`), 네트워크 없는 순수 함수 테스트 + quickstart 수동 점검

**Target Platform**: Windows 10/11, 작업 스케줄러(SYSTEM, 시작 시 실행), `pythonw`

**Project Type**: 상시 실행 단일 프로세스 (백그라운드 워커 + 내장 웹 UI)

**Performance Goals**: 키워드 20개를 1분 주기 안에 조회 (요청 간격 2초 → 최대 약 40초 + 응답 시간)

**Constraints**: 추가 비용 0, 게임 체감 영향 없음(메모리 수십 MB, 대부분 sleep), 관리 화면 인터넷 비노출

**Scale/Scope**: 사용자 1명, 키워드 ≤ 20, 파이썬 파일 2개 + 테스트 1개 + 정적 파일 3개

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 원칙 | 확인 | 결과 |
|---|---|---|
| I. intent.md 우선 | 범위가 intent 1단계와 일치. 필터·알림 기록·자체 앱 없음. 조회 개수 30→120 변경은 intent에 먼저 반영함 | ✅ |
| II. 단순함 우선 | 의존성 `cryptography` 1개(근거: R3). 프레임워크·DB 없음. 파일 최소 | ✅ |
| III. 조회 계층 분리 | `mercari.search(keyword) -> list[Item]` 하나로 격리 ([contract](./contracts/mercari-search.md)) | ✅ |
| IV. 조용한 실패 금지 | 로그 파일 + 10분 연속 실패 경고 + 키워드별 예외 격리 | ✅ |
| V. 비밀·노출 관리 | 토픽 `.env`(gitignore), 포트포워딩 금지·방화벽 포트 규칙(LAN·Tailscale만)·Host 검사, 입력 검증·`textContent`, JSON Content-Type으로 CSRF 완화 | ✅ |
| VI. 핵심 로직 최소 테스트 | 판정·묶음·고장 감지·키워드 검증을 `test_alarm.py`로 | ✅ |

Phase 1 설계 후 재확인: 위반 없음. Complexity Tracking 불필요.

## Project Structure

### Documentation (this feature)

```text
specs/001-keyword-alarm/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── web-api.md
│   └── mercari-search.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
alarm.py          # 진입점: .env 로드, 로깅, 조회 루프, 새 상품 판정, 번역, ntfy 전송, 고장 감지,
                  #         키워드 파일·state 읽기/쓰기, 관리 웹 핸들러(ThreadingHTTPServer)
mercari.py        # search(keyword) -> list[Item]  — 메르카리 조회 방식을 아는 유일한 파일 (DPoP 포함)
static/
├── index.html    # 관리 화면 (인라인 CSS/JS)
├── manifest.json
└── icon.png
test_alarm.py     # unittest
requirements.txt  # cryptography
.env.example      # NTFY_TOPIC=, NTFY_SERVER=https://ntfy.sh, PORT=8787
```

**Structure Decision**: 패키지·`src/` 없이 루트 평면 구조. 파일을 나누는 기준은 constitution III(조회 격리)뿐이다.
웹 핸들러는 처음에 `web.py`로 나눌 계획이었으나 구현 중 `alarm.py`에 합쳤다: `py alarm.py`로 실행하면 모듈이
`__main__`으로 올라가는데 `web.py`가 `import alarm`을 하면 모듈이 두 벌 생겨 파일 락이 갈라진다. 판정·고장 감지는 `alarm.py` 안의 순수 함수로 두어 테스트가 직접 import 한다.

### 핵심 함수 (alarm.py)

| 함수 | 역할 | 테스트 |
|---|---|---|
| `decide(state, items, now) -> (state, fresh, saturated)` | 새 상품 판정 + 조회 창 포화 감지 (data-model 규칙) | ✅ |
| `validate_keyword(raw, existing) -> str` | 정규화·검증, 실패 시 `ValueError(메시지)` | ✅ |
| `FailureWatch.should_alert(now) / ok(now) / alerted()` | 고장 감지 | ✅ |
| `run_cycle()` | 키워드별 search → decide → notify → state 저장 (키워드별 try/except) | 수동 |
| `translate(text) -> str \| None` | Google 번역 비공식 주소, 실패 시 None (research R4a) | 수동 |
| `item_message(item, translated) -> str` | 알림 본문 조립 (번역 유무 분기) | ✅ |
| `notify(title, message, click)` | ntfy JSON POST, 실패 시 예외 | 수동 |

## Complexity Tracking

위반 없음.
