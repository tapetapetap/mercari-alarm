# mercari-alarm

일본 메르카리에 키워드에 맞는 새 상품이 올라오면 1~2분 안에 폰으로 알려 주는 개인용 알림기.
맥북이 깨어 있는 동안 실행되고, 알림은 [ntfy](https://ntfy.sh) 앱으로 받으며(상품명 한국어 번역 + 원문),
키워드는 폰 홈 화면에 추가한 관리 화면에서 등록·삭제한다.

- 설치·동작 확인: [quickstart](specs/002-macos-runtime/quickstart.md)
- 왜·어디까지: [intent.md](intent.md) / 설계: [specs/001-keyword-alarm](specs/001-keyword-alarm/)
- Windows 실행: [quickstart 부록](specs/002-macos-runtime/quickstart.md#부록-windows에서-실행하기)
- 테스트: `.venv/bin/python -m unittest -v`

> `ポケモンカード`처럼 아주 넓은 키워드는 1분 사이 갱신이 120건을 넘으면 새 상품을 놓칠 수 있다.
> 구체적인 키워드를 쓰자 (놓쳤을 가능성은 `alarm.log`에 경고로 남는다).
