#!/bin/bash
# macOS 빌드: 프로젝트 루트에서  bash packaging/mac/build_mac.sh
# 결과: dist/MouseBridge.app, dist/MouseBridge.dmg
# 디버그(콘솔 표시):  MB_CONSOLE=1 bash packaging/mac/build_mac.sh  → 터미널에서 dist/MouseBridge.app/Contents/MacOS/MouseBridge 직접 실행
set -e
cd "$(dirname "$0")/../.."
python3 -m pip install -r requirements.txt pyinstaller --quiet
python3 -m PyInstaller --noconfirm --distpath dist --workpath build packaging/mousebridge.spec

APP=dist/MouseBridge.app
# ad-hoc 서명: 서명이 없으면 손쉬운 사용 권한이 실행마다 초기화될 수 있음
codesign --force --deep --sign - "$APP"

# 로그인 시 자동 실행용 LaunchAgent 를 앱 안에 동봉 (install_launchagent.sh 가 복사)
cp packaging/mac/com.chungil.mousebridge.plist "$APP/Contents/Resources/"

rm -f dist/MouseBridge.dmg
STAGE=$(mktemp -d)
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
cp packaging/mac/install_launchagent.sh "$STAGE/"
hdiutil create -volname MouseBridge -srcfolder "$STAGE" -ov -format UDZO dist/MouseBridge.dmg
rm -rf "$STAGE"
echo "완료: dist/MouseBridge.dmg"
