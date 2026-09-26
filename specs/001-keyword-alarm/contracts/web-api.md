# Contract: 키워드 관리 웹 API

알림기 프로세스가 `0.0.0.0:<PORT>`(기본 8787)에서 제공한다. 인증 없음 — 접근 제한은 네트워크(Tailscale·집 LAN)로 한다.
모든 JSON은 UTF-8.

## GET /

관리 화면 `index.html`. 정적 파일 `manifest.json`, `icon.png`도 같은 방식으로 제공.

## GET /api/keywords

```json
200 {"keywords": ["ポケモンカード 151 BOX", "ニンテンドースイッチ2"]}
```

## POST /api/keywords

요청 `Content-Type: application/json` 필수(아니면 415).

```json
{"keyword": "  ポケモンカード 151 BOX "}
```

| 상황 | 응답 |
|---|---|
| 추가됨 (앞뒤 공백 제거 후 저장) | `201 {"keywords": [...]}` |
| 빈 값 / 50자 초과 | `400 {"error": "키워드는 1~50자여야 합니다"}` |
| JSON 아님 / `keyword` 없음 | `400 {"error": "잘못된 요청입니다"}` |
| 이미 있음 | `400 {"error": "이미 등록된 키워드입니다"}` |
| 20개 초과 | `400 {"error": "키워드는 최대 20개까지 등록할 수 있습니다"}` |
| 본문 4KB 초과 | `413` |
| Content-Type이 JSON 아님 | `415` |

## DELETE /api/keywords?keyword=<URL 인코딩>

| 상황 | 응답 |
|---|---|
| 삭제됨 (state도 삭제) | `200 {"keywords": [...]}` |
| 없음 | `404 {"error": "등록되지 않은 키워드입니다"}` |

## 그 외 경로·메서드

`404` (OPTIONS 등 미지원 메서드는 `501`). CORS 헤더는 보내지 않는다(다른 사이트에서의 요청 차단 목적).

## Host 검사 (DNS 리바인딩 차단)

`Host`가 IP, `localhost`, 점 없는 PC 이름, `*.ts.net`이 아니면 모든 요청에 `403`.

> 구현 메모: 입력 거절은 화면이 메시지만 보여주면 되므로 모두 `400`으로 통일했다(처음 설계의 `409` 구분은 쓰는 곳이 없어 제거).

## 화면 요구사항 (index.html)

- 키워드 목록, 각 항목에 삭제 버튼. 입력창 + 추가 버튼. 오류 메시지 표시 영역.
- 키워드는 `textContent`로 넣는다(`innerHTML` 금지, FR-013).
- 폰 폭(360px)에서 가로 스크롤 없음. 버튼 터치 영역 44px 이상.
- `<link rel="manifest">`, `apple-mobile-web-app-capable`, `apple-touch-icon`으로 홈 화면 추가 지원.
