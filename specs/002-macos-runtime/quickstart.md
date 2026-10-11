# Quickstart: 맥북에서 설치·이전·동작 확인

명령은 모두 맥 **터미널**(zsh) 기준. 관리자 권한(`sudo`)은 필요 없다.

## 0. 준비물

- Homebrew 파이썬: `brew install python` (이미 있으면 생략. `/opt/homebrew/bin/python3`가 있으면 됨)
- [Tailscale](https://tailscale.com/download) 맥 앱 설치 → 폰과 **같은 계정**으로 로그인
- Windows에서 가져올 파일 3개: `C:\mercari-alarm\.env`, `keywords.txt`, `state.json`
  (Taildrop·메일·USB 등 아무 방법. 최소한 `.env`의 `NTFY_TOPIC` 값은 있어야 폰 구독을 그대로 쓴다)

## 1. 실행 폴더 만들기 (개발 폴더와 별개)

```bash
git clone https://github.com/tapetapetap/mercari-alarm.git ~/mercari-alarm
cd ~/mercari-alarm                      # 기본 브랜치 develop
/opt/homebrew/bin/python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest            # 마지막 줄 OK
```

Windows에서 가져온 `.env`, `keywords.txt`, `state.json`을 `~/mercari-alarm/`에 넣는다.
`.env`가 없으면 새로 만든다(이 경우 폰 ntfy에서 새 토픽을 구독):

```bash
printf "NTFY_TOPIC=ma-%s\nPORT=8787\n" "$(uuidgen | tr -d - | tr A-Z a-z)" > .env && cat .env
```

## 2. Windows 알림기 끄기 (중복 알림 방지, 필수)

Windows 관리자 PowerShell:

```powershell
Unregister-ScheduledTask -TaskName mercari-alarm -Confirm:$false
Remove-NetFirewallRule -DisplayName mercari-alarm
```

## 3. 수동 실행으로 확인

```bash
cd ~/mercari-alarm && .venv/bin/python alarm.py      # 종료는 Ctrl+C
```

Tailscale IP: 메뉴 막대의 Tailscale 아이콘에서 이 맥의 주소(100.x.x.x) 확인.

| 확인 | 방법 | 기대 결과 |
|---|---|---|
| 관리 화면 | 맥 브라우저 `http://localhost:8787` | Windows에서 쓰던 키워드 목록 |
| 폰 접속 | 폰(Tailscale 켬) `http://<맥의 Tailscale IP>:8787` | 같은 화면, 추가·삭제 가능 |
| 다른 기기 차단 | 같은 와이파이의 다른 기기(Tailscale 끔)에서 `http://<맥의 와이파이 IP>:8787` | 열리지 않음(403) |
| 알림 | 몇 분 대기 | 기존 폰 구독으로 새 상품 알림, 같은 상품 중복 없음 |

## 4. 로그인 시 자동 실행 등록

```bash
cat > ~/Library/LaunchAgents/com.tapetapetap.mercari-alarm.plist <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.tapetapetap.mercari-alarm</string>
  <key>ProgramArguments</key><array>
    <string>/usr/bin/caffeinate</string><string>-i</string>
    <string>$HOME/mercari-alarm/.venv/bin/python</string><string>alarm.py</string>
  </array>
  <key>WorkingDirectory</key><string>$HOME/mercari-alarm</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>60</integer>
  <key>StandardErrorPath</key><string>$HOME/mercari-alarm/alarm.log.stderr</string>
</dict></plist>
EOF
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.tapetapetap.mercari-alarm.plist
```

| 확인 | 방법 | 기대 결과 |
|---|---|---|
| 실행 중 | `launchctl print gui/$(id -u)/com.tapetapetap.mercari-alarm \| grep state` | `state = running` |
| 저절로 안 잠듦 | `pmset -g assertions \| grep caffeinate` | `PreventUserIdleSystemSleep` 항목 있음 |
| 재시동 | 맥 재시동 → 로그인만 하고 5분 | 폰에서 관리 화면 열림 (SC-101) |
| 방치 | 덮개 연 채 30분 손대지 않음 | 알림 계속 옴 (SC-102) |
| 덮개 닫음 | 덮개 닫고 30분 → 열기 | 닫힌 동안 알림 없음, 연 뒤 2분 안에 그 사이 상품 알림, "조회 실패 중" 경고 없음 (SC-103·104) |

폰 홈 화면 아이콘은 `http://<맥의 Tailscale IP>:8787`로 다시 추가한다 (Safari 공유 → 홈 화면에 추가).

## 5. 운영

- **잠깐 자리를 비울 때**: 잠자기 대신 **화면 잠금**(`Ctrl+Cmd+Q`) — 알림기는 계속 돈다.
- **새 코드 반영** (PR 머지 후):

  ```bash
  cd ~/mercari-alarm && git pull && .venv/bin/pip install -r requirements.txt
  launchctl kickstart -k gui/$(id -u)/com.tapetapetap.mercari-alarm
  ```

- **중지 / 제거**: `launchctl bootout gui/$(id -u)/com.tapetapetap.mercari-alarm` (+ plist 파일 삭제)
- 개발은 `~/Desktop/mercari alarm`(또는 Orca worktree)에서. 거기서 수동 실행할 땐 `.env`에 다른 `PORT`·테스트 토픽.

## 문제 해결

- 알림이 안 옴: `~/mercari-alarm/alarm.log` 확인. 시작조차 안 되면 `alarm.log.stderr`(의존성 누락 등).
  `.env`의 `NTFY_TOPIC`이 없으면 60초마다 재시작을 반복한다.
- 관리 화면이 안 열림: 폰 Tailscale 연결, 주소가 맥의 **Tailscale** IP(100.x)인지 확인. 와이파이 IP로는 403이 정상.
- 덮개를 열었는데 알림이 늦음: 깨어난 뒤 첫 주기(최대 1분)를 기다린다. 로그에 "잠자기에서 복귀"가 찍힌다.

## 부록: Windows에서 실행하기

이전 방식 그대로 쓰려면 [001 quickstart](../001-keyword-alarm/quickstart.md) §0~7. (잠자기 감지는 Windows에서 동작하지 않을 수 있다.)
