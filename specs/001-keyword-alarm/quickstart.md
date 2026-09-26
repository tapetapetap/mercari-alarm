# Quickstart: 설치와 동작 확인

## 0. 준비물

- Windows PC (24시간 켜둠), Python 3.12+ (python.org 설치판, "Add to PATH" 체크)
- 폰: [ntfy](https://ntfy.sh) 앱, [Tailscale](https://tailscale.com) 앱
- PC: Tailscale 설치 후 폰과 같은 계정으로 로그인

## 1. 설치 (PC, PowerShell)

```powershell
git clone https://github.com/tapetapetap/mercari-alarm.git C:\mercari-alarm
cd C:\mercari-alarm
py -m pip install -r requirements.txt
```

`.env` 만들기 (토픽은 추측 불가능한 무작위 문자열):

```powershell
$topic = "ma-" + [guid]::NewGuid().ToString("N")
"NTFY_TOPIC=$topic`nPORT=8787" | Out-File -Encoding utf8 .env
$topic   # 폰 ntfy 앱에서 이 토픽을 구독
```

## 2. 네트워크 확인 없이 테스트

```powershell
py -m unittest -v
```

기대: 모든 테스트 통과. (새 상품 판정·묶음·고장 감지·키워드 검증)

## 3. 수동 실행으로 동작 확인

```powershell
py alarm.py
```

| 확인 | 방법 | 기대 결과 |
|---|---|---|
| 관리 화면 | PC 브라우저 `http://localhost:8787` | 빈 키워드 목록 |
| 폰 접속 | 폰(Tailscale 켬, 와이파이 끔) 브라우저 `http://<PC의 Tailscale IP>:8787` | 같은 화면 |
| 키워드 추가 | 폰에서 `ポケモンカード` 추가 | 목록에 즉시 표시, `keywords.txt`에 한 줄 추가 |
| 첫 조회 무알림 | 1~2분 대기 | 알림 없음, `state.json`에 키워드와 `seen` 생성 |
| 새 상품 알림 | 넓은 키워드라 몇 분 안에 새 상품이 올라옴 | 폰에 "제목=키워드, 본문=상품명·가격" 푸시, 누르면 상품 페이지 |
| 삭제 | 폰에서 삭제 | 목록·`keywords.txt`·`state.json`에서 사라지고 이후 알림 없음 |
| 입력 검증 | 빈 값, 51자, 중복 추가 | 추가 안 되고 이유 표시 |
| 고장 감지 | PC 네트워크를 11분 끊었다 다시 연결 | 재연결 후 1분 안에 "알림기 조회 실패 중" 푸시 한 번 |

확인 후 넓은 키워드는 지우고 실제로 쓸 구체적 키워드를 넣는다. `Ctrl+C`로 종료.

## 4. 폰 홈 화면에 추가

- iPhone: Safari로 관리 화면 열기 → 공유 → "홈 화면에 추가"
- Android: Chrome으로 관리 화면 열기 → 메뉴 → "홈 화면에 추가"

## 5. 상시 실행 등록 (관리자 PowerShell)

```powershell
$py = (Get-Command pythonw).Source
$action  = New-ScheduledTaskAction -Execute $py -Argument "alarm.py" -WorkingDirectory "C:\mercari-alarm"
$trigger = New-ScheduledTaskTrigger -AtStartup
$set = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
       -ExecutionTimeLimit 0 -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName "mercari-alarm" -Action $action -Trigger $trigger -Settings $set -User "SYSTEM"
Start-ScheduledTask -TaskName "mercari-alarm"
```

- 방화벽: 첫 실행 때 뜨는 창에서 **"개인 네트워크"만** 허용. 공유기 포트포워딩은 하지 않는다.
- 전원: 설정 → 전원 → 절전 "안 함", 화면 끄기만 설정.

| 확인 | 기대 결과 |
|---|---|
| PC 재부팅 후 로그인하지 않고 5분 대기 | 폰에서 관리 화면이 열림 (SC-006) |
| 작업 관리자 | `pythonw.exe` 실행 중, 화면에 창 없음 |
| 게임 실행 | 체감 차이 없음 (SC-007) |

## 문제 해결

- 알림이 안 옴: `alarm.log` 확인. `401`/`403`이 반복되면 메르카리 조회 방식이 바뀐 것 → `mercari.py` 수정 필요.
- 관리 화면이 안 열림: 폰 Tailscale 연결, PC 방화벽 "개인" 허용, PC의 Tailscale IP(`tailscale ip -4`) 확인.
- 중지: `Stop-ScheduledTask -TaskName mercari-alarm`, 제거: `Unregister-ScheduledTask -TaskName mercari-alarm`.
