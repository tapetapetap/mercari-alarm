<!--
Sync Impact Report
- Version: 1.0.1 → 1.1.0 (MINOR: 실행 환경을 macOS로 변경, 잠자기 공백·접근 제한 명시)
- Changed sections: 대상 환경·기술 제약, V. 비밀·노출 관리 (intent의 루프백·Tailscale 제한 반영)
- 1.0.0: (template) → 1.0.0 최초 제정
- Principles: I. intent.md 우선 / II. 단순함 우선 / III. 조회 계층 분리 /
  IV. 조용한 실패 금지 / V. 비밀·노출 관리 / VI. 핵심 로직 최소 테스트
- Added sections: 대상 환경·기술 제약, 개발 워크플로 (Governance는 템플릿의 기존 섹션에 내용만 채움)
- Removed sections: 없음
- Templates:
  ✅ .specify/templates/tasks-template.md — "Tests OPTIONAL" 문구에 원칙 VI 예외 명시
  ✅ .specify/templates/plan-template.md — Constitution Check가 이 파일을 참조하므로 변경 불필요
  ✅ .specify/templates/spec-template.md — 필수 섹션 변경 없음
  ⚠ .claude/skills/speckit-tasks/SKILL.md — "테스트는 요청 시에만" 규칙 그대로. spec-kit이 관리하는 파일이라
    수정하지 않는다(업그레이드 시 덮어써짐). 스킬이 이 헌법을 읽으므로 원칙 VI가 우선 적용된다.
- Deferred TODOs: 없음
-->

# mercari-alarm Constitution

## Core Principles

### I. intent.md 우선

- 루트의 `intent.md`가 범위의 기준이다. spec·plan·tasks·코드는 intent와 어긋나면 안 된다(MUST).
- intent의 "하지 않는 것"에 있는 기능은 구현하지 않는다(MUST NOT).
- 방향을 바꿀 때는 코드보다 `intent.md`를 먼저 고치고 사용자 승인을 받는다(MUST).

근거: 바이브코딩은 범위가 쉽게 부푼다. 기준 문서 하나로 초반 설계에서 벗어나는 것을 막는다.

### II. 단순함 우선 (YAGNI)

- 해결 순서: 필요 여부 → 이미 있는 코드 → 표준 라이브러리 → 플랫폼 기본 기능 →
  설치된 의존성 → 최소 구현. 앞 단계에서 해결되면 멈춘다(MUST).
- 새 외부 의존성은 표준 라이브러리로 수십 줄 안에 안 되는 경우에만 추가하고,
  plan에 근거를 적는다(MUST).
- 구현이 하나뿐인 인터페이스, "나중을 위한" 설정·추상화를 만들지 않는다(MUST NOT).
  단, 원칙 III의 조회 경계는 예외다.

근거: 1인용 상시 실행 스크립트다. 코드가 적을수록 고장 날 곳도 적다.

### III. 조회 계층 분리

- 메르카리에서 상품 목록을 가져오는 코드는 "키워드 → 상품 목록(ID·이름·가격)"을
  돌려주는 함수 하나로 격리한다(MUST).
- 새 상품 판별·알림·웹 UI는 조회 방식(내부 API인지 Playwright인지)을 알면 안 된다(MUST NOT).

근거: 비공식 API라 언제든 막히거나 바뀔 수 있다. 교체할 때 이 함수만 바꾸면 되어야 한다.

### IV. 조용한 실패 금지

- 조회·알림 실패는 로그 파일에 남긴다(MUST).
- 조회가 10분 이상 연속 실패하면 사용자에게 푸시로 한 번 알리고,
  복구되면 다시 알릴 수 있게 초기화한다(MUST).
- 한 키워드의 실패가 다른 키워드 조회나 웹 UI를 멈추게 하면 안 된다(MUST NOT).

근거: 알림기의 가치는 "안 오면 새 상품이 없다"고 믿을 수 있는 데 있다.
조용히 죽으면 그 믿음이 깨진다.

### V. 비밀·노출 관리

- ntfy 토픽 등 비밀 값은 `.env`에 두고 커밋하지 않는다(MUST NOT commit).
  코드와 문서에는 예시 값만 쓴다.
- 키워드 관리 웹 UI는 인터넷에 노출하지 않는다. 공유기 포트를 열지 않고
  맥북 자신(루프백)·Tailscale 사설망으로만 접근한다(MUST).
- 웹 UI로 들어오는 키워드 입력은 신뢰하지 않는다. 길이·빈 값을 검증하고,
  화면 출력 시 이스케이프한다(MUST).

근거: 토픽이 새면 남이 내 알림을 구독할 수 있고, 관리 화면에는 로그인이 없다.

### VI. 핵심 로직 최소 테스트

- 분기가 있는 핵심 로직(새 상품 판별, 신규 키워드 첫 조회 무알림, 5건 초과 묶음,
  연속 실패 판정, 키워드 입력 검증·추가·삭제)은 실행 가능한 테스트를 하나 이상 남긴다(MUST).
- 테스트는 표준 라이브러리(`unittest`)로 쓰고, 네트워크 없이 돌아야 한다(MUST).
  메르카리·ntfy 실호출 확인은 수동 점검으로 한다.
- 단순 한 줄 코드에는 테스트를 만들지 않는다.

근거: 고장 나도 조용한 로직(중복 알림, 알림 폭탄)을 싸게 잡는다.

## 대상 환경·기술 제약

- 실행 환경: macOS 맥북, Homebrew Python 3 venv, launchd 에이전트 + `caffeinate -i`로 로그인 시 실행.
- 덮개 닫힘·사용자 잠자기는 막지 않는다. 잠든 동안 알림 공백은 intent에서 감수한다.
- 개발 환경은 macOS일 수 있으므로 경로는 `pathlib`, 파일은 UTF-8로 명시해 OS 차이를 없앤다.
- 조회 주기 1분, 키워드 사이 간격을 둔다. 1인 저빈도 원칙을 넘는 조회량을 만들지 않는다.
- 추가 월 비용 0 — 유료 서비스·클라우드를 도입하지 않는다(intent 변경 없이는).

## 개발 워크플로

- brainstorming → spec-kit(`/speckit-specify` → `/speckit-plan` → `/speckit-tasks`)
  → 실사용 변화 설명·승인 → `/speckit-implement` → ponytail-review → `/code-review`.
- 기능 브랜치 → `develop` PR. Claude 코드리뷰 CI 결과를 확인한 뒤 **사용자가 머지**한다.
  `develop` → `main`은 배포 시점에 사용자가 머지한다.
- 커밋 전 `unittest`가 통과해야 한다.

## Governance

- 이 헌법은 다른 관행보다 우선한다. 충돌하면 헌법을 따르거나 헌법을 먼저 개정한다.
- 개정: PR로 변경안과 이유를 올리고 사용자 승인으로 확정한다. 상단 Sync Impact Report를 갱신한다.
- 버전: MAJOR(원칙 삭제·재정의) / MINOR(원칙·섹션 추가) / PATCH(문구 수정).
- 준수 확인: plan의 Constitution Check와 PR 리뷰에서 원칙 I~VI 위반 여부를 확인한다.
  위반이 불가피하면 plan의 Complexity Tracking에 근거를 적는다.

**Version**: 1.1.0 | **Ratified**: 2026-09-26 | **Last Amended**: 2026-10-04
