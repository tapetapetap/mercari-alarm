# Tasks: 키워드별 알림 멈춤

**Input**: Design documents from `/specs/004-keyword-pause/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [contracts/web-api.md](./contracts/web-api.md), [quickstart.md](./quickstart.md)

**Tests**: constitution VI — 멈춤 저장·조회 제외·state 처리는 분기 로직이라 `unittest`.

---

## Phase 1: Setup

- [X] T001 [P] `.gitignore`에 `paused.txt` 추가

---

## Phase 3: User Story 1 — 키워드를 지우지 않고 잠시 멈추기 (Priority: P1) 🎯 MVP

**Independent Test**: quickstart §3 표.

### Tests

- [X] T002 [US1] `test_alarm.py` `KeywordTest`(임시 폴더)에 `PAUSED_FILE`도 임시 경로로 바꾸고 테스트 추가:
  (a) `set_paused("A", True)` → `paused.txt`에 A, `load_paused()` == ["A"], A의 state 삭제;
  (b) 다시 `True` → 중복 없음; (c) `set_paused("A", False)` → 빈 목록;
  (d) 미등록 키워드 → `KeyError`; (e) `remove_keyword("A")`가 `paused.txt`에서도 지움;
  (f) `paused.txt`에 `keywords.txt`에 없는 줄이 있으면 `load_paused()`가 무시;
  (g) `check_keyword`(가짜 `mercari.search`)가 조회 중 키워드가 멈춰지면 state를 쓰지 않음;
  (h) `run_cycle`(가짜 `mercari.search`, `GAP` 0)이 멈춘 키워드는 조회하지 않음

### Implementation

- [X] T003 [US1] `alarm.py`: `PAUSED_FILE = BASE / "paused.txt"`, `load_paused()`(현재 키워드에 있는 것만, 순서 유지),
  `save_paused(list)`(`_write`), `set_paused(keyword, paused)`(lock 안에서: 미등록이면 `KeyError`, 추가/제거 후 저장,
  멈출 때 state에서 그 키워드 pop), `remove_keyword`가 `paused.txt`에서도 제거 — research R1·R2
- [X] T004 [US1] `alarm.py` `run_cycle`: 조회 대상은 `keywords - paused`, `not active`면 `watch.ok`.
  `check_keyword`의 마지막 기록 검사에 `keyword in load_paused()`면 쓰지 않음 추가 — research R3
- [X] T005 [US1] `alarm.py` 웹: 키워드 응답 공통 헬퍼로 `{"keywords", "paused", "max"}`. `do_POST`에서 `/api/pause` 처리
  (`keyword` str, `paused` bool 아니면 400, 미등록 404). JSON 본문 파싱은 `/api/keywords`와 공유 — contracts/web-api.md
- [X] T006 [US1] `static/index.html`: `render(keywords, max, paused)`, 행마다 `멈춤`/`재개` 버튼(`call("POST", "/api/pause", ...)`),
  멈춘 행은 흐리게 + "· 멈춤" 표시, `aria-label`에 키워드. 안내 문구에 "멈춘 키워드는 재개한 뒤 올라온 상품부터 알립니다" 추가

---

## Phase 4: Polish

- [X] T007 `~/mercari-alarm/.venv/bin/python -m unittest -v` 전체 통과
- [X] T008 로컬 스모크: 임시 폴더에 복사, 다른 `PORT`·가짜 토픽으로 실행해 `curl`로 `/api/pause` 200·400·404·415 확인, `ntfy` 전송 없이 (키워드 없이 실행)
- [X] T009 [P] `specs/001-keyword-alarm/contracts/web-api.md` 끝에 "004에서 `paused`·`POST /api/pause` 추가" 링크 한 줄

---

## Dependencies & Execution Order

- T001 언제든. T002 → T003 → T004 → T005 → T006 → T007 → T008. T009 언제든.

## Implementation Strategy

- 한 PR(`004-keyword-pause` → `develop`). 머지 후 실행 폴더 갱신.
