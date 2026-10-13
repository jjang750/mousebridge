#!/bin/bash
# 로그인 시 자동 실행 등록 (선택). 앱을 /Applications 에 복사한 뒤 실행.
set -e
PL=~/Library/LaunchAgents/com.chungil.mousebridge.plist
mkdir -p ~/Library/LaunchAgents
cp /Applications/MouseBridge.app/Contents/Resources/com.chungil.mousebridge.plist "$PL"
launchctl unload "$PL" 2>/dev/null || true
launchctl load "$PL"
echo "등록 완료. 해제: launchctl unload $PL && rm $PL"
