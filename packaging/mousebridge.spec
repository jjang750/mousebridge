# -*- mode: python ; coding: utf-8 -*-
# 공용 PyInstaller spec. Windows / macOS 각각에서:  pyinstaller packaging/mousebridge.spec
import os
import sys
from PyInstaller.utils.hooks import collect_submodules
block_cipher = None
CONSOLE = os.environ.get("MB_CONSOLE") == "1"   # 디버그: 콘솔 창 표시

hidden = (collect_submodules("pynput") + collect_submodules("pystray")
          + collect_submodules("zeroconf") + collect_submodules("screeninfo")
          + ["ifaddr", "PIL", "PIL.Image", "PIL.ImageDraw"])
if sys.platform == "darwin":
    hidden += ["AppKit", "Quartz", "Foundation", "objc", "ApplicationServices", "HIServices"]

a = Analysis(["../run_app.py"], pathex=[".."], hiddenimports=hidden,
             excludes=["tkinter", "matplotlib", "numpy"], cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if sys.platform == "darwin":
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="MouseBridge",
              console=CONSOLE, target_arch=None)
    coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, name="MouseBridge")
    app = BUNDLE(coll, name="MouseBridge.app", bundle_identifier="com.chungil.mousebridge",
                 info_plist={
                     "CFBundleName": "MouseBridge",
                     "CFBundleShortVersionString": "0.4.0",
                     "LSUIElement": True,                       # Dock 아이콘 숨김(메뉴바 앱)
                     "NSHighResolutionCapable": True,
                     "NSAppleEventsUsageDescription": "입력 공유를 위해 필요합니다.",
                     # macOS 14/15 로컬 네트워크 권한: 설명 + Bonjour 서비스명이 없으면 조용히 거부됨
                     "NSLocalNetworkUsageDescription": "같은 네트워크의 상대 PC 를 찾고 입력을 전송하기 위해 필요합니다.",
                     "NSBonjourServices": ["_mousebridge._tcp"],
                     "LSMultipleInstancesProhibited": True,
                 })
else:
    # Windows: onedir + UPX 비활성 + 버전 리소스 -> Defender 오탐 완화
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="MouseBridge",
              console=CONSOLE, uac_admin=False, upx=False, icon=None,
              version="windows/version_info.txt")
    coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, upx=False, name="MouseBridge")
