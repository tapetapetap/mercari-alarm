# Implementation Plan: 키워드별 알림 멈춤

**Branch**: `004-keyword-pause` | **Date**: 2026-10-15 | **Spec**: [spec.md](./spec.md)

## Summary

멈춘 키워드를 `paused.txt`(한 줄에 하나)에 저장한다. `run_cycle`은 멈춘 키워드를 건너뛰고, 멈출 때 그 키워드의 `state`를 지워
재개 후 첫 조회가 "첫 조회 무알림" 규칙(001)을 그대로 타게 한다. API는 `POST /api/pause` 하나, 화면은 행마다 버튼 하나.

## Technical Context

**Language/Version**: Python 3 (Homebrew 3.14 venv) · 정적 HTML/JS
**Primary Dependencies**: 표준 라이브러리만
**Storage**: `paused.txt` (UTF-8, gitignore) — research R1
**Testing**: `unittest` (네트워크 없음)
**Target Platform**: macOS launchd (002)
**Project Type**: 단일 스크립트 + 정적 관리 화면
**Constraints**: 비용 0, 새 의존성 0
**Scale/Scope**: 키워드 최대 20

## Constitution Check

| 원칙 | 판단 |
|---|---|
| I. intent 우선 | 키워드 관리 화면의 연장. intent "하지 않는 것"과 충돌 없음. 통과 |
| II. 단순함 | 파일 하나·API 하나·버튼 하나. 예약 재개·전체 멈춤 안 함. 통과 |
| III. 조회 계층 분리 | `mercari.py` 무관. 통과 |
| IV. 조용한 실패 금지 | 모두 멈춤이면 조회 0 → 경고 안 보냄은 "키워드 없음"과 같은 의도된 상태. 통과 |
| V. 비밀·노출 | 새 API도 기존 IP·Host·JSON 검사를 거침. 키워드는 `textContent`로만 출력. 통과 |
| VI. 최소 테스트 | 멈춤/재개/삭제 시 파일·state 변화, 멈춘 키워드 조회 제외, 조회 중 멈춤 시 state 미기록에 테스트. 통과 |

## Project Structure

```text
specs/004-keyword-pause/  spec.md plan.md research.md contracts/web-api.md quickstart.md tasks.md
alarm.py           # PAUSED_FILE, load/save_paused, set_paused, remove_keyword·run_cycle·check_keyword 수정, POST /api/pause
static/index.html  # 행마다 멈춤/재개 버튼, 멈춘 행 흐리게
test_alarm.py      # PauseTest
.gitignore         # paused.txt
```

data-model 별도 파일 없음: 저장 데이터는 `paused.txt` 한 줄 목록뿐 (research R1).

## Complexity Tracking

없음.
