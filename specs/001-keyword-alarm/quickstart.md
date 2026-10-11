> 현재 실행 환경은 맥북 — [002 quickstart](../002-macos-runtime/quickstart.md) 참조.

# Quickstart: 설치와 동작 확인

명령은 모두 **PowerShell** 기준이다. "관리자"라고 적힌 단계만 관리자 권한 PowerShell(시작 메뉴에서 우클릭 → 관리자 권한으로 실행)에서 실행한다.

## 0. 준비물

- Windows PC (24시간 켜둠)
- Python 3.12+ — [python.org](https://www.python.org/downloads/) 설치판. 설치 첫 화면에서 **"Add python.exe to PATH" 체크**
- Git — `winget install --id Git.Git -e`
- [Tailscale](https://tailscale.com/download) — PC와 폰에 설치, **같은 계정**으로 로그인
- 폰: [ntfy](https://ntfy.sh) 앱

설치 후 PowerShell을 새로 연다 (PATH 반영).

## 1. 설치

```powershell
git clone https://github.com/tapetapetap/mercari-alarm.git C:\mercari-alarm
cd C:\mercari-alarm
py -m pip install -r requirements.txt
```

비공개 저장소라 처음 클론할 때 GitHub 로그인 창이 뜬다. 기본 브랜치(`develop`)가 받아진다.

`.env` 만들기 (토픽은 추측 불가능한 무작위 문자열):

```powershell
$topic = "ma-" + [guid]::NewGuid().ToString("N")
"NTFY_TOPIC=$topic`nPORT=8787" | Out-File -Encoding utf8 .env
$topic   # 폰 ntfy 앱에서 + 버튼 → 이 토픽 구독 (서버는 기본값 ntfy.sh)
```

## 2. 방화벽 (관리자)

```powershell
New-NetFirewallRule -DisplayName "mercari-alarm" -Direction Inbound -Protocol TCP -LocalPort 8787 `
  -RemoteAddress LocalSubnet,100.64.0.0/10 -Action Allow
```

- 집 LAN과 Tailscale(100.64.0.0/10)에서만 8787 포트를 연다. **공유기 포트포워딩은 하지 않는다.**
- 첫 실행 때 뜨는 방화벽 허용 창에 의존하지 않는다: 그 허용은 `python.exe`에만 걸리고, 상시 실행(§6)은
  창 없는 `pythonw.exe`를 SYSTEM 계정으로 돌려 허용 창도 뜨지 않으므로 폰에서 접속이 막힌다. 포트 기준 규칙이 둘 다 덮는다.
  (허용 창이 뜨면 "취소"를 눌러도 된다.)

## 3. 네트워크 없이 테스트

```powershell
py -m unittest -v
```

기대: 모든 테스트 통과. (새 상품 판정·묶음·번역 문구·고장 감지·키워드 검증·Host 검사)

## 4. 수동 실행으로 동작 확인

```powershell
py alarm.py          # 실행 상태 유지, 종료는 Ctrl+C
tailscale ip -4      # 다른 PowerShell 창에서: PC의 Tailscale IP(100.x.x.x)
```

| 확인 | 방법 | 기대 결과 |
|---|---|---|
| 관리 화면 | PC 브라우저 `http://localhost:8787` | 빈 키워드 목록 |
| 폰 접속 | 폰(Tailscale 켬, 와이파이 끔) 브라우저 `http://<PC의 Tailscale IP>:8787` | 같은 화면 |
| 키워드 추가 | 폰에서 `ポケモンカード` 추가 | 목록에 즉시 표시, `keywords.txt`에 한 줄 추가 |
| 첫 조회 무알림 | 1~2분 대기 | 알림 없음, `state.json`에 키워드와 `seen` 생성 |
| 새 상품 알림 | 넓은 키워드라 몇 분 안에 새 상품이 올라옴 | 폰에 "제목=키워드, 본문=번역 상품명·가격·(원문)" 푸시, 누르면 상품 페이지. 번역이 실패하면(구글 번역 제한 등) 원문·가격 두 줄로 온다 |
| 삭제 | 폰에서 삭제 | 목록·`keywords.txt`·`state.json`에서 사라지고 이후 알림 없음 |
| 입력 검증 | 빈 값, 51자, 중복 추가 | 추가 안 되고 이유 표시 |
| 고장 감지 | PC 네트워크를 11분 끊었다 다시 연결 | 재연결 후 1분 안에 "알림기 조회 실패 중" 푸시 한 번 |

확인 후 넓은 키워드는 지우고 실제로 쓸 구체적 키워드를 넣는다. `Ctrl+C`로 종료.

## 5. 폰 홈 화면에 추가

- iPhone: Safari로 관리 화면 열기 → 공유 → "홈 화면에 추가"
- Android: Chrome으로 관리 화면 열기 → 메뉴(⋮) → "홈 화면에 추가"

## 6. 상시 실행 등록 (관리자)

```powershell
$py = (Get-Command pythonw).Source
$action  = New-ScheduledTaskAction -Execute $py -Argument "alarm.py" -WorkingDirectory "C:\mercari-alarm"
$trigger = New-ScheduledTaskTrigger -AtStartup
$set = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
       -ExecutionTimeLimit 0 -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName "mercari-alarm" -Action $action -Trigger $trigger -Settings $set -User "SYSTEM"
Start-ScheduledTask -TaskName "mercari-alarm"
```

- 전원: 설정 → 시스템 → 전원 → 절전 "안 함", 화면 끄기만 설정.

| 확인 | 기대 결과 |
|---|---|
| PC 재부팅 후 로그인하지 않고 5분 대기 | 폰에서 관리 화면이 열림 (SC-006) |
| 작업 관리자 | `pythonw.exe` 실행 중, 화면에 창 없음 |
| 게임 실행 | 체감 차이 없음 (SC-007) |

## 7. 실행 폴더와 개발 폴더 분리

- **`C:\mercari-alarm`은 실행 전용.** 작업 스케줄러가 이 폴더의 코드를 돌리고 `.env`·`keywords.txt`·`state.json`·`alarm.log`가 여기 쌓인다.
  이 폴더에서 브랜치를 바꾸면 알림기도 그 코드로 돈다 → 항상 `develop`에 둔다.
- **개발은 별도 worktree(예: Orca)에서.** 거기서 수동 실행할 때는 `.env`에 다른 `PORT`(예: 18787)와 테스트용 토픽을 써서
  실행 중인 알림기와 겹치지 않게 한다.
- **새 코드 반영**: PR 머지 후

  ```powershell
  cd C:\mercari-alarm; git pull
  py -m pip install -r requirements.txt   # 의존성이 바뀌었을 때를 대비해 매번
  Stop-ScheduledTask mercari-alarm; Start-ScheduledTask mercari-alarm
  ```

## 문제 해결

- 알림이 안 옴: `alarm.log` 확인. `401`/`403`이 반복되면 메르카리 조회 방식이 바뀐 것 → `mercari.py` 수정 필요.
  작업 스케줄러에 "마지막 실행 결과"가 실패(0x1)면 `.env`의 `NTFY_TOPIC`이 없는 것.
- 관리 화면이 안 열림: 폰 Tailscale 연결, §2 방화벽 규칙(`Get-NetFirewallRule -DisplayName mercari-alarm`),
  PC의 Tailscale IP(`tailscale ip -4`) 확인. 주소는 IP·PC 이름·`*.ts.net`만 허용된다(그 외 이름은 403).
- 중지: `Stop-ScheduledTask -TaskName mercari-alarm`, 제거: `Unregister-ScheduledTask -TaskName mercari-alarm`.
