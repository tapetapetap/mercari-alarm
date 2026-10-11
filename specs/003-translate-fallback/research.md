# Research: 번역 차단 대응

## R1. 번역 주소

- **Decision**: `https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=ja&tl=ko&q=<text>`
- **Rationale**: 2026-10-11 같은 맥북에서 `translate.googleapis.com`(gtx, `/single`·`/t`)과 `translate.google.com`(gtx)은
  모두 429("Sorry..." 페이지)였지만 이 주소는 200. 응답은 JSON 문자열 배열 `["번역문"]`(sl 지정 시).
  `&`·따옴표·`<`도 HTML 이스케이프 없이 그대로 온다(`<`는 JSON `<`로 와서 `json.load`가 풀어줌). 문장이 여러 개여도 한 문자열.
- **Alternatives considered**:
  - MyMemory(`api.mymemory.translated.net`): 200이었지만 익명 하루 5,000자 한도 — 하루 개별 알림 수십~100건이면 닿을 수 있음.
    브랜드명 번역 품질도 낮음(`アプレッセ` → `Appressé`). 기각.
  - 두 주소를 차례로 시도하는 대체 체인: 구현이 둘이 되고, 둘 다 비공식이라 안정성 이득이 작다. YAGNI, 기각.
  - 유료 API(DeepL·Google Cloud): 비용 0 원칙 위반, 기각.

## R2. 차단 시 쉬기

- **Decision**: `HTTPError` 코드 429면 모듈 변수 `_translate_paused_until = time.monotonic() + 3600`, 경고 로그 한 번.
  `translate()` 시작에서 그 시각 전이면 바로 `None`.
- **Rationale**: 막힌 동안 요청을 계속하면 차단이 연장되기 쉽고, 상품당 왕복 시간이 낭비된다. 1시간은 구글 차단의 흔한 지속 시간 추정.
  `monotonic` 기준이라 맥북이 잠든 시간은 쉬는 시간에 들어가지 않는다 — 깨어난 뒤 남은 시간만큼 더 쉰다. 감수(차단 해제 확인을 늦게 할 뿐).
- **Alternatives considered**: 지수 백오프(구현 대비 이득 작음), `state.json` 저장(재시작이 드물다), 벽시계 기준(시계 변경에 취약).
