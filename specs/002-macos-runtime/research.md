# Research: 알림기 실행 위치를 맥북으로 이전

2026-10-04, 사용자 맥북(Mac17,9, macOS 26.6.2)에서 확인.

## R1. 로그인 시 자동 시작·재시작

- **Decision**: 사용자 launchd 에이전트 `~/Library/LaunchAgents/com.tapetapetap.mercari-alarm.plist`.
  `RunAtLoad=true`(로그인 시 시작), `KeepAlive=true`(죽으면 재시작), `ThrottleInterval=60`(재시작 간격 60초),
  `WorkingDirectory`=실행 폴더, `StandardErrorPath`=`alarm.log.stderr`(파이썬이 로깅을 시작하기 전 실패 — 예: 의존성 누락 — 를 남김).
- **Rationale**: macOS 기본 기능, 설치 없음. 창·Dock 아이콘 없음(FR-104). `ThrottleInterval`이 없으면 기본 10초라
  `.env` 누락처럼 계속 실패하는 경우 재시작이 잦다.
- **Alternatives**: 로그인 항목(재시작 없음), 시스템 데몬 `/Library/LaunchDaemons`(로그인 없이도 돌지만 관리자 권한 필요,
  들고 다니는 맥북에서 로그인 없는 실행은 이득 없음), Homebrew services(설치 필요).

## R2. 덮개가 열린 동안 저절로 잠들지 않기

- **Decision**: plist의 실행 명령을 `/usr/bin/caffeinate -i <venv python> alarm.py`로 한다.
- **확인**: `man caffeinate` — `-i`는 "idle sleep 방지" assertion. `-s`는 "system sleep 방지(AC 전원일 때만)".
  `-i`는 덮개 닫힘·사용자의 잠자기 선택을 막지 않는다(FR-103). `-s`는 전원 연결 시 덮개를 닫아도 깨어 있게 할 수 있어 가방 속 발열 위험 → 탈락.
- caffeinate는 자식 프로세스가 끝나면 같은 종료 코드로 끝나므로 launchd 재시작 동작은 그대로다.
- 현재 맥북 설정 `sleep 1`(1분 무조작 시 잠자기) — caffeinate 없이는 1분 만에 알림이 멈춘다.
- **Alternatives**: `pmset` 전역 설정 변경(관리자 권한, 알림기를 꺼도 설정이 남음), 파이썬에서 IOKit 호출(코드 증가).

## R3. 잠자기 감지 (FR-106)

- **Decision**: 두 시계의 차이로 실제 잠든 시간을 잰다.
  `slept = (time.time() 증가분) - (time.monotonic() 증가분)`. 1분(60초) 이상이면 잠자기에서 깬 것으로 본다.
- **확인**: 이 맥북의 `time.get_clock_info('monotonic')` = `mach_absolute_time()` — 잠든 동안 멈춘다.
  `time.time()`(벽시계)은 잠든 동안에도 흐른다. 따라서 차이 = 잠든 시간.
- **Rationale**: 처음 생각한 "주기 간격이 3분 이상이면"은 조회가 느린 경우(타임아웃 15초 × 키워드 20개)에도 걸려,
  실제 고장 중에 기준이 계속 재설정되어 **경고가 영영 안 가는** 버그가 된다. 두 시계 차이는 느린 조회에선 0이다.
  주기 도중에 잠들어도 잡힌다.
- 판정은 주기 시작과 경고 판단 직전에 한다. NTP 보정 같은 벽시계 점프는 보통 1분 미만이라 무시된다.
- Windows(QueryPerformanceCounter)에서는 잠든 시간이 monotonic에 포함될 수 있어 감지가 안 될 수 있다 — Windows는 이제 부록용이라 감수.

## R4. 관리 화면 접근 제한 (FR-109)

- **Decision**: 요청한 쪽 IP(`client_address[0]`)가 루프백(`127.0.0.0/8`)이거나 Tailscale(`100.64.0.0/10`)일 때만 처리, 아니면 `403`.
  기존 Host 검사도 유지.
- **Rationale**: 서버는 `0.0.0.0`(IPv4)에서 듣는다. Tailscale 주소에만 바인딩하면 Tailscale이 늦게 켜질 때 서버가 못 뜬다.
  앱에서 IP를 거르는 게 가장 단순하고 네트워크 상태와 무관하다. macOS 방화벽은 현재 꺼져 있어 의존하지 않는다.
- 집 와이파이에서 Tailscale 없이 접속하던 경로는 없어진다(spec Assumptions).
- **Alternatives**: macOS 방화벽(앱 단위 허용만 가능, IP 범위 불가), pf 규칙(관리자·복잡), 비밀번호 추가(intent "로그인 없음" 범위 밖).

## R5. 파이썬과 실행 폴더

- **Decision**: 실행 폴더 `~/mercari-alarm`(별도 클론, `develop` 고정), 가상환경 `~/mercari-alarm/.venv`를
  `/opt/homebrew/bin/python3`로 만든다.
- **Rationale**: 이 맥북의 기본 `python3`는 miniforge(conda base) — 환경을 바꾸면 경로가 흔들린다. Homebrew 파이썬은 경로가 고정이고,
  가상환경 안의 절대 경로를 plist에 적으면 launchd의 PATH와 무관하다.
- `.venv/`를 `.gitignore`에 추가.

## R6. Windows에서 옮기기

- **Decision**: `.env`(토픽), `keywords.txt`, `state.json` 세 파일을 맥북 실행 폴더로 복사(Taildrop·메일·USB 등 아무 방법).
  이후 Windows에서 `Unregister-ScheduledTask` + 방화벽 규칙 제거.
- 최소 요건은 토픽(`.env`)이다. `state.json`을 못 옮겨도 키워드를 다시 넣으면 첫 조회 무알림 규칙 덕에 알림 폭탄은 없고,
  이전 중 올라온 상품 몇 개를 놓칠 뿐이다.
