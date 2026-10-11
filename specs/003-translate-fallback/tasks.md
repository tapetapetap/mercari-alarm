# Tasks: 번역 차단 대응

**Input**: Design documents from `/specs/003-translate-fallback/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [quickstart.md](./quickstart.md)

**Tests**: constitution VI — 쉬기 분기와 응답 파싱은 분기 로직이라 `unittest`를 둔다 (`urlopen`을 가짜로 바꿔 네트워크 없이).

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup / Phase 2: Foundational

없음 (기존 코드 위에서 작업).

---

## Phase 3: User Story 1 — 알림을 다시 한국어로 받기 (Priority: P1) 🎯 MVP

**Goal**: 번역 주소를 지금 동작하는 주소로 교체.

**Independent Test**: quickstart §3 "번역 복구" 행.

- [X] T001 [P] [US1] `test_alarm.py`에 `TranslateTest`: `alarm.urllib.request.urlopen`을 가짜로 바꿔 (a) 응답 `["번역문"]` → `"번역문"`,
  (b) 요청 URL 호스트가 `clients5.google.com`이고 `client=dict-chrome-ex`, `sl=ja`, `tl=ko`, `q=<원문>` 포함,
  (c) 빈 응답 `[""]` → `None`
- [X] T002 [US1] `alarm.py` `translate()`: URL을 `https://clients5.google.com/translate_a/t?` + `client=dict-chrome-ex&sl=ja&tl=ko&q=`로,
  응답 `json.load(res)[0]`(문자열) 사용, 빈 문자열이면 `None`. docstring의 research 참조를 `003 research R1`로 — T001 통과

---

## Phase 4: User Story 2 — 차단당하면 잠시 쉬기 (Priority: P2)

**Goal**: 429면 1시간 번역 요청 중단, 로그 한 번.

**Independent Test**: quickstart §1 (T003 테스트).

- [X] T003 [US2] `test_alarm.py` `TranslateTest`에 추가: (a) 가짜 `urlopen`이 `HTTPError 429` → `None`, 경고 로그 1건,
  이어서 같은 monotonic 시각에 다시 호출하면 `urlopen` 호출 0회·로그 0건, (b) `alarm.time.monotonic`을 3600초 뒤로 바꾸면 다시 호출됨,
  (c) `TimeoutError`/`HTTPError 500`은 쉬지 않음(다음 호출에서 `urlopen` 다시 불림). 각 테스트는 `alarm._translate_paused_until`을 0으로 초기화
- [X] T004 [US2] `alarm.py`: 상수 `TRANSLATE_COOLDOWN = 3600`, 모듈 변수 `_translate_paused_until = 0.0`.
  `translate()` 처음에 `time.monotonic() < _translate_paused_until`이면 `None`. `urllib.error.HTTPError`이고 `code == 429`면
  `_translate_paused_until = time.monotonic() + TRANSLATE_COOLDOWN`, `log.warning("번역 차단(429), %d분 동안 원문으로 알림", ...)` (traceback 없음) 후 `None`.
  그 외 예외는 기존대로 — T003 통과

---

## Phase 5: Polish

- [X] T005 `~/mercari-alarm/.venv/bin/python -m unittest -v` 전체 통과
- [X] T006 [P] `specs/001-keyword-alarm/research.md` R4a에 "번역 주소는 003 research R1로 교체됨" 한 줄

---

## Dependencies & Execution Order

- T001 → T002 → T003 → T004 → T005. T006은 언제든.
- US2는 US1과 같은 함수를 고치므로 순서대로.

## Implementation Strategy

- US1만으로 번역 복구(MVP). US2는 같은 PR에 함께.
- 한 PR(`003-translate-fallback` → `develop`). PR #6(002) 위에 쌓였으므로 #6 머지 후 diff가 이 작업만 남는다.
