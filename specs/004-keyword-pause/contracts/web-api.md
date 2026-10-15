# Contract: 키워드 멈춤 API (001 web-api에 추가)

기존 [001 contract](../../001-keyword-alarm/contracts/web-api.md)의 IP·Host 검사, JSON·크기 검사를 그대로 따른다.

## 모든 키워드 응답에 `paused` 추가

`GET /api/keywords`, `POST /api/keywords`, `DELETE /api/keywords`, `POST /api/pause` 모두:

```json
200 {"keywords": ["A", "B"], "paused": ["A"], "max": 20}
```

`paused`는 `keywords`의 부분집합.

## POST /api/pause

요청 `Content-Type: application/json` 필수(아니면 415), 본문 4KB 이하(아니면 413).

```json
{"keyword": "A", "paused": true}
```

| 상황 | 응답 |
|---|---|
| 멈춤/재개됨 (이미 그 상태여도 성공) | `200 {"keywords", "paused", "max"}` |
| JSON 아님 / `keyword`가 문자열 아님 / `paused`가 bool 아님 | `400 {"error": "잘못된 요청입니다"}` |
| 등록되지 않은 키워드 | `404 {"error": "등록되지 않은 키워드입니다"}` |

멈출 때 그 키워드의 state를 지운다 (research R2).

## 화면

- 각 행: 키워드, `멈춤`(재생 중) 또는 `재개`(멈춘 상태) 버튼, `삭제` 버튼.
- 멈춘 행은 키워드를 흐리게 + "멈춤" 표시. `aria-label`에 키워드 포함.
- 폰 폭 360px에서 가로 스크롤 없음, 버튼 터치 영역 44px.
