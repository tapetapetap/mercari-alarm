# Implementation Plan: 번역 차단 대응

**Branch**: `003-translate-fallback` | **Date**: 2026-10-11 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-translate-fallback/spec.md`

## Summary

`alarm.py`의 `translate()`만 바꾼다. 번역 주소를 지금 동작하는 구글 무료 주소(`clients5` / `dict-chrome-ex`)로 옮기고,
429를 받으면 1시간 동안 번역 요청을 보내지 않는다(모듈 변수 하나). 나머지 흐름(`item_message`, 사이클당 번역 예산)은 그대로.

## Technical Context

**Language/Version**: Python 3 (Homebrew 3.14, 맥북 venv)
**Primary Dependencies**: 표준 라이브러리(`urllib`, `json`) — 추가 없음
**Storage**: 없음 (쉬는 시각은 메모리에만)
**Testing**: `unittest`, 네트워크 없이 `urllib.request.urlopen`을 가짜로 바꿔 검사
**Target Platform**: macOS launchd 에이전트 (002)
**Project Type**: 단일 상시 실행 스크립트
**Performance Goals**: 차단 중 상품당 번역 대기 0초
**Constraints**: 비용 0, 새 의존성 0
**Scale/Scope**: `translate()` 한 함수 + 테스트 몇 개

## Constitution Check

| 원칙 | 판단 |
|---|---|
| I. intent 우선 | 번역은 intent 1단계 범위 안. 동작 변경 아님(복구). 통과 |
| II. 단순함 | 주소 교체 + 모듈 변수 하나. 대체 번역 체인·영속 저장 안 함. 통과 |
| III. 조회 계층 분리 | `mercari.py` 무관. 통과 |
| IV. 조용한 실패 금지 | 차단 시작을 로그에 한 번 남김, 다른 실패는 기존대로 로그. 통과 |
| V. 비밀·노출 | 상품명만 보냄(기존과 같음). 통과 |
| VI. 최소 테스트 | 쉬기 분기(429 → 쉼 → 1시간 뒤 재시도, 다른 오류는 안 쉼)와 응답 파싱에 테스트. 통과 |

설계 후 재확인: 변화 없음.

## Project Structure

### Documentation (this feature)

```text
specs/003-translate-fallback/
├── spec.md
├── plan.md
├── research.md
├── quickstart.md
└── tasks.md
```

data-model·contracts 없음: 저장 데이터·외부 인터페이스 변화가 없다 (쉬는 시각은 메모리 변수 하나, research R2).

### Source Code (repository root)

```text
alarm.py        # translate()와 TRANSLATE_COOLDOWN 상수
test_alarm.py   # TranslateTest
```

**Structure Decision**: 기존 단일 파일 구조 유지.

## Complexity Tracking

없음.
