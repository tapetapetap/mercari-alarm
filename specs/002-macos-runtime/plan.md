# Implementation Plan: 알림기 실행 위치를 맥북으로 이전

**Branch**: `002-macos-runtime` | **Date**: 2026-10-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-macos-runtime/spec.md`

## Summary

코드 변경은 `alarm.py` 두 곳뿐: (1) `FailureWatch.tick()` — 벽시계와 monotonic 시계의 차이로 잠든 시간을 재서
1분 이상이면 실패 기준을 재설정, (2) 관리 웹이 루프백·Tailscale(100.64.0.0/10) IP만 받도록. 나머지는 운영 변경:
launchd 에이전트 + `caffeinate -i`로 로그인 시 실행·덮개 열린 동안 잠들지 않기, 실행 폴더 `~/mercari-alarm` + venv,
Windows 데이터 이전·해제 절차(quickstart).

## Technical Context

**Language/Version**: Python 3 (Homebrew `/opt/homebrew/bin/python3`, venv) — 001과 동일 코드

**Primary Dependencies**: 변화 없음 (`cryptography` 1개). 운영: macOS 기본 `launchd`, `caffeinate`

**Storage**: 변화 없음 (`keywords.txt`, `state.json`, `.env`, `alarm.log*`). 실행 폴더 `~/mercari-alarm`

**Testing**: `unittest` — `FailureWatch.tick()`, IP 제한 함수 추가. 잠자기·launchd는 quickstart 수동 점검

**Target Platform**: macOS 26 (Apple Silicon 맥북), 사용자 로그인 세션

**Project Type**: 기존 단일 프로세스 그대로

**Performance Goals**: 변화 없음

**Constraints**: 덮개 닫힘·사용자 잠자기를 막지 않음(FR-103), 관리자 권한 불필요, 추가 비용 0

**Scale/Scope**: `alarm.py` 약 +20줄, 테스트 약 +25줄, 문서(quickstart·README·constitution·001 문서 참조)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 원칙 | 확인 | 결과 |
|---|---|---|
| I. intent.md 우선 | intent를 먼저 고침(8677d34): 실행 위치=맥북, 잠든 동안 공백 감수, 접근 제한 강화. 범위 밖 기능 없음 | ✅ |
| II. 단순함 우선 | 새 의존성 0. launchd·caffeinate는 OS 기본. 잠자기 감지는 표준 라이브러리 시계 2개 | ✅ |
| III. 조회 계층 분리 | `mercari.py` 변경 없음 | ✅ |
| IV. 조용한 실패 금지 | 잘못된 경고 제거하되 실제 고장은 깨어난 뒤 10분이면 경고. 시작 실패는 `alarm.log.stderr`에 남음 | ✅ |
| V. 비밀·노출 관리 | 공용 와이파이 노출을 IP 제한으로 막음(강화). `.env` 계속 gitignore | ✅ |
| VI. 핵심 로직 최소 테스트 | `tick()`(잠자기 vs 느린 조회), IP 제한에 테스트 | ✅ |
| 대상 환경·기술 제약 | **constitution이 "집 Windows PC"로 적혀 있음 → 이 PR에서 macOS로 개정 (v1.1.0, MINOR)** | ⚠ → 개정으로 해소 |

Phase 1 이후 재확인: 위반 없음.

## Project Structure

### Documentation (this feature)

```text
specs/002-macos-runtime/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md          # macOS 설치·이전 (Windows는 001 quickstart로 연결한 부록)
├── contracts/web-access.md
└── tasks.md               # /speckit-tasks
```

### Source Code (변경 파일)

```text
alarm.py          # FailureWatch.tick(), SLEEP_GAP=60; client_allowed(ip); Handler._route에서 IP 검사
test_alarm.py     # tick·client_allowed 테스트
.gitignore        # .venv/
README.md         # quickstart 링크를 002로
.specify/memory/constitution.md   # 대상 환경 → macOS (v1.1.0)
specs/001-keyword-alarm/contracts/web-api.md   # IP 제한 참조 (작성 완료)
```

**Structure Decision**: 새 파일 없음. launchd plist는 사용자 경로가 들어가므로 저장소에 두지 않고 quickstart의 명령이 `$HOME`으로 생성한다.

### 핵심 변경 (alarm.py)

| 항목 | 내용 | 테스트 |
|---|---|---|
| `FailureWatch.__init__(now, mono)` | `last_wall`, `last_mono` 추가 | ✅ |
| `FailureWatch.tick(wall, mono) -> float` | 잠든 초 반환, `SLEEP_GAP` 이상이면 `last_success = wall` | ✅ |
| `run_cycle` | 시작과 경고 판단 직전에 `tick`, 잠자기면 로그 | 수동 |
| `client_allowed(ip) -> bool` | `127.0.0.0/8` 또는 `100.64.0.0/10` | ✅ |
| `Handler._route` | `client_allowed` 실패 → 403 (Host 검사보다 먼저) | 수동(quickstart §3) |

## Complexity Tracking

위반 없음.
