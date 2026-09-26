# Data Model: 메르카리 키워드 신착 알림기 (1단계)

모든 파일은 프로젝트 폴더에 UTF-8로 저장한다. `keywords.txt`, `state.json`, `.env`, `alarm.log`는 `.gitignore` 대상.

## Keyword — `keywords.txt`

한 줄에 키워드 하나. 사용자가 메모장으로 직접 고쳐도 된다.

```text
ポケモンカード 151 BOX
ニンテンドースイッチ2
```

| 규칙 | 값 |
|---|---|
| 정규화 | 앞뒤 공백 제거. 빈 줄은 무시 |
| 길이 | 1~50자 |
| 중복 | 정확히 같은 문자열만 중복 (대소문자·전각/반각 다르면 다른 키워드) |
| 개수 | 최대 20개 |

파일을 직접 고쳐 규칙을 어기면(51자, 21번째 줄 등) 조회 시 앞에서부터 규칙에 맞는 것만 쓰고, 나머지는 로그에 경고한다.

## KeywordState — `state.json`

```json
{
  "ポケモンカード 151 BOX": {
    "since": 1790420000,
    "seen": ["m86965730291", "2JXKVGE8hWCMUBFzhZnQgP"]
  }
}
```

| 필드 | 뜻 |
|---|---|
| `since` | 이 키워드의 첫 조회 성공 시각(유닉스 초). 이 시각 - 60초 이전에 등록된 상품은 알리지 않음 |
| `seen` | 이미 본 상품 ID. 최신이 뒤. 최대 500개(넘으면 앞에서 버림) |

**상태 전이**

```text
(키워드 없음) --웹/파일로 추가--> (등록됨, state 없음)
(등록됨, state 없음) --첫 조회 성공--> (state 생성: since=now, seen=결과 ID 전부, 알림 없음)
(state 있음) --조회 성공--> 새 상품 판정 → 알림 → 전송 성공분만 seen에 추가
(state 있음) --키워드 삭제--> state 삭제
state.json에 있으나 keywords.txt에 없는 키워드 → 다음 주기에 state 삭제 (메모장 삭제 대응)
```

## Item — 조회 결과 (메모리)

| 필드 | 출처(API) | 비고 |
|---|---|---|
| `id` | `items[].id` | |
| `name` | `items[].name` | |
| `price` | `items[].price` | 정수 엔 |
| `created` | `items[].created` | 유닉스 초(정수) |
| `shops` | `items[].itemType == "ITEM_TYPE_BEYOND"` | bool |
| `url` | 파생 | 일반 `https://jp.mercari.com/item/<id>`, Shops `https://jp.mercari.com/shops/product/<id>` |

## 새 상품 판정 규칙

```text
unseen   = [i for i in items if i.id not in seen]
new      = [i for i in unseen if i.created >= since - 60]     # 목록 순서(최신 갱신 먼저) 유지
old_bump = unseen - new                                       # 알리지 않고 seen에만 추가
개별 알림 = new[:5], 묶음 알림 = len(new) - 5 (> 0일 때만)
포화     = state가 있고 len(items) > 0 이며 모든 item이 unseen   # 1분 사이 120건 넘게 갱신 → 놓쳤을 수 있음, 로그 경고
seen에 추가 = old_bump + 전송 성공한 개별 알림 상품 + (묶음 전송 성공 시) new[5:]
```

## Notification — ntfy 메시지

| 종류 | title | message | click |
|---|---|---|---|
| 새 상품 | 키워드 | `상품명\n¥12,345` | 상품 URL |
| 묶음 | 키워드 | `외 N건의 새 상품` | 키워드 검색 URL(`https://jp.mercari.com/search?keyword=<인코딩>&sort=created_time&order=desc&status=on_sale`) |
| 고장 경고 | `알림기 조회 실패 중` | `N분째 메르카리 조회가 실패하고 있습니다. alarm.log를 확인하세요.` | 없음 |

## FailureWatch — 메모리

| 필드 | 초기값 | 규칙 |
|---|---|---|
| `last_success` | 프로세스 시작 시각 | 키워드 조회가 하나라도 성공하면 now. 키워드가 0개인 주기도 now로 갱신 |
| `alerted` | false | `now - last_success ≥ 600`이고 false면 경고 전송 시도 → 성공 시 true. 조회 성공 시 false |
