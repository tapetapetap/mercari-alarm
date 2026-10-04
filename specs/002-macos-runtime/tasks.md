# Tasks: 알림기 실행 위치를 맥북으로 이전

**Input**: Design documents from `/specs/002-macos-runtime/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/web-access.md](./contracts/web-access.md), [quickstart.md](./quickstart.md)

**Tests**: constitution VI — 잠자기 감지(`tick`)와 IP 제한(`client_allowed`)은 분기 로직이라 `unittest`를 둔다.
launchd·caffeinate·실제 잠자기는 quickstart 수동 점검.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 다른 파일이고 미완료 작업에 의존하지 않아 병렬 가능
- **[Story]**: US1(깨어 있는 동안 알림), US2(잠자기 복귀), US3(접근 제한), US4(Windows 이전)

---

## Phase 1: Setup

- [X] T001 [P] `.gitignore`에 `.venv/` 추가
- [X] T002 [P] `.specify/memory/constitution.md` "대상 환경·기술 제약"의 실행 환경을 macOS(맥북, launchd 에이전트 + `caffeinate -i`,
  Homebrew 파이썬 venv)로 개정, 잠든 동안 공백은 intent에서 감수함을 명시, v1.0.1 → v1.1.0, Sync Impact Report 갱신

---

## Phase 2: Foundational

없음 (기존 코드 위에서 작업).

---

## Phase 3: User Story 2 — 잠자기 후 깨어날 때 자연스럽게 이어지기 (Priority: P1) 🎯

US1(상시 실행)은 운영 설정이라 코드가 없고, 맥북에서 돌리면 US2 문제(깨어날 때 잘못된 경고)가 바로 생기므로 코드 작업을 먼저 한다.

**Goal**: 잠든 동안 멈춰 있던 시간 때문에 "조회 실패 중" 경고가 가지 않게 한다.

**Independent Test**: quickstart §4 "덮개 닫음" 행.

### Tests for User Story 2

- [X] T003 [P] [US2] `test_alarm.py`에 `FailureWatch.tick` 테스트: (a) 벽시계·monotonic이 같이 600초 흐름(느린 조회) → 잠든 시간 0,
  `last_success` 유지, 이후 `should_alert` True, (b) 벽시계 3600초·monotonic 60초(잠자기 3540초) → 반환값 3540,
  `last_success`=깨어난 시각, 직후 `should_alert` False, 그 뒤 600초 실패 시 True, (c) 잠든 시간 59초 → 재설정 안 함,
  (d) 기존 `FailureWatchTest`가 새 생성자 인자로 계속 통과

### Implementation for User Story 2

- [X] T004 [US2] `alarm.py`: 상수 `SLEEP_GAP = 60`, `FailureWatch.__init__(self, now, mono=None)`에 `last_wall`/`last_mono` 추가
  (`mono` 기본값 `time.monotonic()`), `tick(self, wall, mono) -> float`(data-model 규칙, 잠든 초 반환) — T003 통과
- [X] T005 [US2] `alarm.py`의 `run_cycle`: 시작과 경고 판단 직전에 `watch.tick(time.time(), time.monotonic())`,
  `SLEEP_GAP` 이상이면 `log.info("잠자기에서 복귀 (%d분)")`. `main()`의 `FailureWatch(time.time())`는 그대로 동작해야 함

**Checkpoint**: 깨어난 직후 실패해도 경고 없음, 실제 고장은 깨어난 뒤 10분에 경고

---

## Phase 4: User Story 3 — 밖에서도 관리 화면은 나만 열기 (Priority: P2)

**Goal**: 루프백·Tailscale 외 IP의 요청을 모두 403.

**Independent Test**: quickstart §3 "다른 기기 차단" 행.

### Tests for User Story 3

- [X] T006 [P] [US3] `test_alarm.py`에 `client_allowed` 테스트: 허용 `127.0.0.1`, `100.64.0.1`, `100.127.255.254`, `100.101.102.103`;
  거절 `192.168.0.10`, `10.0.0.5`, `100.63.255.255`, `100.128.0.1`, `8.8.8.8`, 형식 오류 문자열

### Implementation for User Story 3

- [X] T007 [US3] `alarm.py`: `TAILSCALE_NET = ipaddress.ip_network("100.64.0.0/10")`, `client_allowed(ip) -> bool`(루프백 또는 Tailscale,
  형식 오류는 False), `Handler._route`에서 Host 검사보다 먼저 `client_allowed(self.client_address[0])` 실패 시 403 — T006 통과
  ([contracts/web-access.md](./contracts/web-access.md))

**Checkpoint**: 같은 와이파이의 다른 기기 차단

---

## Phase 5: User Story 1·4 — 상시 실행과 Windows 이전 (운영, P1·P2)

코드 변경 없음. 절차는 [quickstart.md](./quickstart.md)에 작성 완료.

- [ ] T008 [US1] 개발 맥에서 스모크: 임시 실행 폴더(scratchpad)에 복사 → venv → `caffeinate -i python alarm.py` 실행 →
  `pmset -g assertions`에 `PreventUserIdleSystemSleep` 확인, `localhost` 관리 화면 200, 와이파이 IP로 접속 403, 테스트 토픽 알림 수신
- [ ] T009 [P] [US4] `README.md`: 실행 환경을 맥북으로, quickstart 링크를 `specs/002-macos-runtime/quickstart.md`로, Windows는 부록 링크

---

## Phase 6: Polish

- [ ] T010 `.venv/bin/python -m unittest -v` 전체 통과 (개발 폴더에서는 scratchpad venv)
- [ ] T011 [P] `specs/001-keyword-alarm/quickstart.md` 맨 위에 "현재 실행 환경은 맥북 — 002 quickstart 참조" 한 줄 안내

---

## Dependencies & Execution Order

- Setup(T001·T002) → US2(T003→T004→T005) → US3(T006→T007) → 운영(T008·T009) → Polish
- US2와 US3는 같은 `alarm.py`를 고치므로 순서대로. 테스트(T003·T006)는 각자 구현 전에.

### Parallel Opportunities

- T001, T002 동시 / T003과 T006 동시 작성 가능 / T009, T011 동시

## Implementation Strategy

- 코드(US2·US3)를 한 PR로 만들고, 사용자가 머지 후 quickstart대로 맥북에 설치(US1·US4)한다.
- 설치 직후 확인: quickstart §3 표, §4 표.
