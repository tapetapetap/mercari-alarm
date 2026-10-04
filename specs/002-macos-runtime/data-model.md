# Data Model: 알림기 실행 위치를 맥북으로 이전

001의 [data-model](../001-keyword-alarm/data-model.md)과 같다. 바뀌는 것은 고장 감지 상태(메모리)뿐이다.

## FailureWatch — 메모리 (확장)

| 필드 | 초기값 | 규칙 |
|---|---|---|
| `last_success` | 시작 시각(벽시계) | 조회 성공·키워드 0개면 now. **잠자기 감지 시 깨어난 시각으로 재설정** |
| `alerted` | false | 기존과 같음 (경고 성공 시 true, `ok()` 시 false) |
| `last_wall`, `last_mono` | 시작 시각의 `time.time()`, `time.monotonic()` | `tick()` 호출마다 갱신 |

**잠자기 감지** — `tick(wall, mono)`:

```text
slept = (wall - last_wall) - (mono - last_mono)
if slept >= SLEEP_GAP (60초):   last_success = wall   → True 반환(로그 "잠자기에서 복귀, N분")
last_wall, last_mono = wall, mono
```

호출 위치: 주기 시작, 경고 판단 직전.

## 파일 (실행 폴더 `~/mercari-alarm`)

001과 같은 `.env`, `keywords.txt`, `state.json`, `alarm.log*`에 더해:

| 파일 | 뜻 |
|---|---|
| `.venv/` | 파이썬 가상환경 (`cryptography`) — gitignore |
| `alarm.log.stderr` | launchd가 받는 표준 에러. 로깅 시작 전 실패 기록 — `alarm.log*`로 gitignore |
