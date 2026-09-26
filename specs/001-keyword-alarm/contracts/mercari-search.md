# Contract: 메르카리 조회 경계 (constitution III)

조회 방식을 아는 코드는 `mercari.py` 하나뿐이다. 나머지 코드는 아래 함수만 쓴다.

```python
def search(keyword: str) -> list[Item]:
    """판매 중 상품을 최근 갱신순으로 최대 120개 돌려준다. 실패하면 예외를 던진다."""
```

- `Item`: `id: str`, `name: str`, `price: int`, `created: int`(유닉스 초), `shops: bool`, `url: str`
  ([data-model.md](../data-model.md#item--조회-결과-메모리) 참조)
- 실패(네트워크 오류, 4xx/5xx, 응답 형식 이상)는 예외. 호출자가 잡아서 로그·고장 감지에 반영한다.
- 타임아웃 15초.

## 현재 구현: 내부 검색 API

[research.md R1·R3](../research.md) 참조. 메르카리가 막거나 바꾸면 이 파일만 Playwright 구현으로 교체한다.
