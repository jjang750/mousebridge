# MouseBridge

Windows ↔ macOS 마우스/키보드 공유. LAN(TCP) 기반 양방향, mDNS 자동 탐색, USB HID 기반 키맵.

기본 배치: **Mac(왼쪽, 대기측) — Windows(오른쪽, 접속측)**. `config.json` 으로 변경.

## 설치 (릴리스 바이너리)
GitHub Releases 에서 다운로드. `v*` 태그를 푸시하면 GitHub Actions 가 자동 빌드합니다.
- Windows: `MouseBridge-Setup.exe` (로그인 자동 실행·방화벽 예외 옵션)
- macOS: `MouseBridge.dmg` → Applications 로 드래그

### macOS 권한 (필수)
시스템 설정 > 개인정보 보호 및 보안에서 **손쉬운 사용 / 입력 모니터링 / 로컬 네트워크** 에 MouseBridge 허용 후 앱 재시작.
- 터미널에서 `Contents/MacOS/MouseBridge` 를 직접 실행하면 터미널 권한을 빌려 쓰므로 테스트 결과가 다릅니다. 항상 `open` 또는 Finder 로 실행해 검증하세요.
- 재빌드/재설치 후 권한이 풀리면 목록에서 제거 후 재추가. 초기화: `tccutil reset Accessibility com.chungil.mousebridge`
- ad-hoc 서명이므로 첫 실행은 우클릭 > 열기, 또는 `xattr -dr com.apple.quarantine /Applications/MouseBridge.app`

### Windows 주의
- 서명이 없어 SmartScreen 경고가 뜨면 "추가 정보 > 실행". **스마트 앱 컨트롤**이 켜진 PC 에서는 공인 코드 서명 없이는 실행되지 않습니다(끄거나 `python run_app.py` 로 실행).
- 관리자 권한 창 위에서는 입력 주입이 막힙니다(OS 정책).

## 설정
- Windows: `%APPDATA%\MouseBridge\config.json` · macOS: `~/Library/Application Support/MouseBridge/config.json`
- 트레이/메뉴바 아이콘에서 "설정 파일 열기" / "로그 열기"

```jsonc
{
  "role": "listen",         // listen(대기) | connect(접속)   Mac 기본 listen, Win 기본 connect
  "my_position": "left",    // 내 PC 위치: left | right | top | bottom
  "peer_host": "",          // 접속측만. 비우면 mDNS 자동 탐색 (IP 지정 시 즉시 연결)
  "port": 24800,
  "swap_cmd_ctrl": true,    // Ctrl<->Cmd 교환
  "hangul_mac": "kana",     // Mac 수신 시 한/영: kana | capslock | ctrl-space | cmd-space
  "verbose": false
}
```

## 개발
```bash
pip install -e ".[dev]"
pytest
python run_app.py                                        # 트레이 앱 (config.json)
python -m bridge.main --listen  --my-position left -v    # CLI
python -m bridge.main --connect --my-position right -v   # HOST 생략 시 mDNS
```

### 로컬 빌드
```powershell
powershell -ExecutionPolicy Bypass -File packaging\windows\build_win.ps1   # Windows
```
```bash
bash packaging/mac/build_mac.sh                                            # macOS
```
디버그(콘솔 표시): `MB_CONSOLE=1` 환경변수를 주고 빌드.

## 구조
```
bridge/
├─ app.py        설치형 진입점 (트레이, 권한 검사, DPI)
├─ main.py       CLI 진입점
├─ bridge.py     LOCAL/REMOTE/CONTROLLED 상태머신, 프레임 처리
├─ net.py        listen/connect 루프, 자동 재연결
├─ discovery.py  mDNS 광고/탐색
├─ capture.py    OS 훅 입력 캡처 (Windows LL hook / macOS event tap)
├─ inject.py     입력 주입
├─ keymap.py     HID usage <-> Win VK / Mac keycode
├─ proto.py      바이너리 프레임 프로토콜
├─ config.py     설정 파일
└─ log.py        로깅
```

## 프로토콜
`[2B length][1B type][payload]` — HELLO(해상도), ENTER(진입 가장자리+비율), MOVE(dx,dy), BUTTON, WHEEL, KEY(HID usage), LEAVE, PING/PONG

## 로드맵
- [ ] TLS + 핀 페어링 (현재 평문 TCP, 신뢰 네트워크 전용)
- [ ] 클립보드 텍스트 공유
- [ ] 모니터별 경계 인식 (현재 가상 화면 외곽만)
- [ ] 공인 코드 서명

## License
MIT
