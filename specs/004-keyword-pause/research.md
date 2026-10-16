# Research: 키워드별 알림 멈춤

## R1. 멈춤 상태 저장 위치

- **Decision**: `paused.txt`, 한 줄에 키워드 하나. 읽을 때 `keywords.txt`에 있는 것만 유효.
- **Rationale**: 기존 `keywords.txt`·`_write`(원자적 교체) 패턴 재사용. 사람이 열어 봐도 바로 보인다.
- **Alternatives considered**:
  - `keywords.txt` 줄 앞 표시(`#` 등): 키워드 자체가 `#`으로 시작할 수 있어 모호. 기각.
  - `state.json`에 넣기: state는 키워드별 기억이고 멈출 때 지우는 대상이라 섞이면 정리 로직이 꼬인다. 기각.

## R2. 재개 후 몰림 방지

- **Decision**: 멈출 때 그 키워드의 state를 지운다. 재개 후 첫 조회는 state가 없으니 001의 "첫 조회 무알림"으로 기준만 잡는다.
- **Rationale**: 새 코드 없이 기존 규칙 재사용. 멈춘 동안 상품을 알리지 않는다는 spec Assumption과 일치.
- **Alternatives considered**: 멈춘 동안에도 조회해 seen만 갱신 — 조회량 그대로, 멈춤의 의미가 약함. 기각.

## R3. 조회 도중 멈춤

- **Decision**: `check_keyword`가 state를 쓰기 직전 "삭제됐는지" 검사에 "멈췄는지"를 더한다.
- **Rationale**: 멈춘 뒤 옛 state가 다시 기록되면 재개 시 멈춘 동안 상품이 몰려온다(R2 깨짐).
- **보완 (PR #8 리뷰)**: 판정 직후·전송 전에 한 번 더 멈춤 여부를 확인해 보내지 않는다. 남는 틈은 그 확인 뒤 번역·전송 중(최대 5건, 수 초)뿐.

## R4. API 모양

- **Decision**: `POST /api/pause` `{"keyword": "...", "paused": true|false}` → `200 {"keywords", "paused", "max"}`.
- **Rationale**: 기존 POST의 JSON·크기 검사를 그대로 탄다(CSRF 대응 동일). 켜고 끄기를 한 엔드포인트로.

## R5. 메모장으로 지운 키워드의 옛 멈춤 표시

- **Decision**: `add_keyword`가 추가한 키워드를 `paused.txt`에서 지운다(이때 다른 옛 줄도 정리). `remove_keyword`는 `paused.txt`를 건드리지 않는다.
- **Rationale**: 옛 줄이 문제 되는 순간은 같은 키워드를 다시 추가할 때뿐이다. 한 곳에서 처리하면 웹 삭제·메모장 삭제 둘 다 덮인다.
- **한계**: 메모장으로 지웠다가 웹이 아니라 메모장으로 다시 적으면 옛 멈춤이 남는다. 화면에 "멈춤"으로 보이므로 재개를 누르면 된다.
