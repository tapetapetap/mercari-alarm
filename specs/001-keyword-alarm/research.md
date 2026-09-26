# Research: 메르카리 키워드 신착 알림기 (1단계)

Phase 0. Technical Context의 미정 사항을 정리한다. 메르카리 조회는 2026-09-26에 실제 호출로 확인했다.

## R1. 메르카리 검색 조회 방법

- **Decision**: `POST https://api.mercari.jp/v2/entities:search`를 직접 호출한다.
  - 헤더: `DPoP: <JWT>`, `X-Platform: web`, `Content-Type: application/json`
  - 본문 핵심: `searchCondition.keyword`, `sort: SORT_CREATED_TIME`, `order: ORDER_DESC`,
    `status: [STATUS_ON_SALE]`, `pageSize: 120`, `defaultDatasets: [DATASET_TYPE_MERCARI, DATASET_TYPE_BEYOND]`
  - 응답 `items[]`: `id`, `name`, `price`(문자열, 엔), `created`/`updated`(유닉스 초, 문자열),
    `status`, `itemType`(`ITEM_TYPE_MERCARI` | `ITEM_TYPE_BEYOND`=Shops)
- **확인 결과**:
  - DPoP 헤더가 없으면 `401 unauthorized: missing auth token`. 있으면 `200`.
  - `SORT_CREATED_TIME`은 실제로 **`updated` 내림차순**이다. 가격 수정된 오래된 상품이 위로 올라온다
    (`created=1790059779`인 상품이 최근 `updated`로 상위에 있음).
  - 구체 키워드(`ポケモンカード 151 BOX`) 120건은 약 29시간 분량. 넓은 키워드(`ポケモンカード`)는 몇 초에 여러 건 갱신.
  - Shops 상품 ID는 영숫자(`2JXKVGE8hWCMUBFzhZnQgP`), 일반 상품은 `m` + 숫자.
- **Rationale**: 요청 1회에 JSON 수십 KB, 1분 주기에 부담 없음. 헤드리스 브라우저보다 훨씬 가볍다.
- **Alternatives**: Playwright로 검색 페이지 렌더링(무거움, constitution III에 따라 교체 후보로만 유지),
  HTML 파싱(목록이 JS 렌더링이라 불가), 비공식 라이브러리 `mercapi`(유지보수 불확실, 필요한 건 요청 1종뿐).

## R2. "새 상품" 판정 (updated 정렬 대응)

- **Decision**: 키워드별 상태에 `since`(첫 조회 시각)와 `seen`(상품 ID 목록)을 둔다.
  새 상품 = `id ∉ seen` **그리고** `created ≥ since - 60초`. 조건을 못 넘은 미확인 상품은 알리지 않고 `seen`에만 넣는다.
- **Rationale**: ID만 보면 가격 수정으로 올라온 옛 상품이 "새 상품"으로 알림된다. `created` 조건으로 걸러낸다.
  60초 여유는 PC 시계와 메르카리 시계의 작은 차이를 흡수한다.
- `seen`은 키워드당 최근 500개만 유지(조회 120개의 4배 이상). 오래된 ID가 밀려나도 `created < since` 조건 덕에 다시 알리지 않는다.
- **Alternatives**: 마지막 조회 시각 이후 `created`만 보기(ID 기억 없이) — PC 시계 오차·조회 실패 구간에서 누락/중복이 생겨 탈락.

## R3. DPoP 서명 (ES256)

- **Decision**: `cryptography` 패키지로 P-256 키를 프로세스 시작 시 1회 생성하고, 요청마다 JWT를 서명한다.
  JWT 헤더 `{typ: dpop+jwt, alg: ES256, jwk}`, 페이로드 `{iat, jti, htu, htm: POST, uuid}`.
- **Rationale**: 표준 라이브러리에는 ECDSA가 없다. 직접 구현은 30줄 남짓 가능하지만 암호 코드를 손으로 쓰는 건
  "영리한 코드"이고, `cryptography`는 Windows용 wheel이 있는 사실상 표준이다. constitution II의 "새 의존성 근거" 충족.
- **Alternatives**: 순수 Python ECDSA 직접 구현(탈락: 검증 부담), `ecdsa` 패키지(유지보수 약함), `PyJWT`(결국 `cryptography` 필요).

## R4. 푸시 전송 (ntfy)

- **Decision**: `POST https://ntfy.sh/`에 JSON 본문 `{topic, title, message, click}`을 보낸다(`urllib.request`).
- **Rationale**: 헤더 방식(`Title:`)은 비ASCII(일본어·한국어) 인코딩이 번거롭다. JSON 방식은 UTF-8 그대로 된다.
  `click` URL을 누르면 폰 기본 동작으로 링크가 열린다.
- 토픽은 `.env`의 `NTFY_TOPIC`(무작위 문자열), 서버는 `NTFY_SERVER`(기본 `https://ntfy.sh`).

## R4a. 상품명 번역

- **Decision**: `GET https://translate.googleapis.com/translate_a/single?client=gtx&sl=ja&tl=ko&dt=t&q=<상품명>`
  (`urllib.request`, 타임아웃 5초). 응답 `d[0][*][0]`을 이어 붙인 것이 번역문. 실패·형식 이상이면 `None` → 원문만 표시.
- **확인**(2026-09-26): `ポケモンカード151 BOX シュリンク付き 未開封` → `포켓몬 카드 151 BOX 슈링크 첨부 미개봉`.
- **Rationale**: 가입·키·설치 없음. 월 약 12만 자 수준이라 부담 없음.
- **Alternatives**: DeepL API Free(가입·카드 인증), Google Cloud Translation(결제 계정), 로컬 번역 모델(수백 MB, 과함).

## R5. 관리 화면 서버

- **Decision**: 표준 라이브러리 `http.server.ThreadingHTTPServer`를 조회 루프와 같은 프로세스의 별도 스레드로 띄운다.
  `0.0.0.0:<PORT>`(기본 8787)에서 듣고, 접근 제한은 네트워크로 한다: 공유기 포트포워딩 없음 + Windows 방화벽은 "개인" 프로필만 허용.
  Tailscale IP(100.x)와 집 LAN에서 접속된다.
- **CSRF 완화**: POST는 `Content-Type: application/json`만 받는다. 브라우저의 다른 사이트 요청은 CORS preflight가 필요한데
  서버가 응답하지 않으므로 막힌다. DELETE도 preflight 대상이다.
- **Rationale**: 요청은 하루 몇 번. 웹 프레임워크(Flask 등)는 과하다.
- **Alternatives**: Flask/FastAPI(의존성 추가, 이득 없음), 별도 프로세스(키워드 파일 동시 접근 관리가 더 복잡).

## R6. PWA (홈 화면 추가)

- **Decision**: `index.html` 한 장 + `manifest.json` + 아이콘 1개. 서비스 워커는 두지 않는다.
- **Rationale**: iOS Safari의 "홈 화면에 추가"는 manifest/apple 메타태그로 충분하다. Android Chrome도 서비스 워커 없이
  바로가기 추가가 된다. 오프라인 동작은 의미가 없다(PC에 연결돼야 키워드를 바꿀 수 있음).

## R7. Windows 상시 실행

- **Decision**: 작업 스케줄러 — 트리거 "시스템 시작 시", "사용자의 로그온 여부에 관계없이 실행",
  실패 시 1분마다 재시작(최대 999회), 실행 시간 제한 해제. 동작은 `pythonw.exe alarm.py`(창 없음), 시작 위치=프로젝트 폴더.
  등록은 quickstart의 PowerShell `Register-ScheduledTask` 한 블록으로 한다.
- 전원: 절전 "안 함", 모니터 끄기만 설정. 네트워크 어댑터 절전 해제.
- **Alternatives**: Windows 서비스(NSSM 등 추가 도구 필요), 시작프로그램 폴더(로그인해야 실행돼 FR-020 위반).

## R8. 파일·동시성

- **Decision**: `keywords.txt`(UTF-8, 한 줄에 하나), `state.json`(키워드별 `since`/`seen`). 쓰기는 임시 파일에 쓴 뒤
  `os.replace`로 교체(원자적). 웹 스레드와 조회 스레드는 `threading.Lock` 하나로 두 파일 접근을 직렬화.
- 고장 감지 상태(마지막 성공 시각·경고 여부)는 메모리에만 둔다. 재시작하면 "방금 시작" 기준으로 다시 잰다.
- 로그: `logging` + `RotatingFileHandler`(`alarm.log`, 1MB × 3).

## R9. 테스트

- **Decision**: `unittest` 한 파일(`test_alarm.py`). 네트워크 없이 순수 함수만 검증:
  새 상품 판정(첫 조회 무알림, `created` 필터, 중복 방지, 500개 제한), 5건 초과 묶음, 고장 감지 타이밍, 키워드 검증.
- 메르카리·ntfy 실호출은 quickstart의 수동 점검으로 확인.
