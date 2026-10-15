# Quickstart: 키워드 멈춤 확인

## 1. 테스트

```bash
~/mercari-alarm/.venv/bin/python -m unittest -v
```

## 2. 반영

PR 머지 후 [002 quickstart](../002-macos-runtime/quickstart.md)의 "새 코드 반영" 절차.

## 3. 실사용 확인

| 확인 | 방법 | 기대 결과 |
|---|---|---|
| 멈춤 | 폰 관리 화면에서 키워드 A "멈춤" | A 행이 흐려지고 버튼이 "재개"로, `paused.txt`에 A |
| 조회 제외 | 2분 뒤 `grep "'A'" ~/mercari-alarm/alarm.log \| tail` | 멈춘 뒤 A 알림 기록 없음, 다른 키워드는 계속 |
| 재시작 유지 | `launchctl kickstart -k gui/$(id -u)/com.tapetapetap.mercari-alarm` 후 화면 새로 고침 | A 여전히 멈춤 |
| 재개 | "재개" | 버튼이 "멈춤"으로, 몇 분 동안 몰린 알림 없이 이후 새 상품부터 알림 |
| 삭제 | 멈춘 A 삭제 | 목록·`paused.txt`에서 사라짐 |
