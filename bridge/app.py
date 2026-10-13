"""설치형 진입점: config.json 기반 실행 + 트레이/메뉴바 아이콘."""
import logging
import subprocess
import sys
import threading

from . import __version__, config, log as logcfg

log = logging.getLogger("app")
IS_WIN = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"


def _set_dpi_aware():
    """Windows: PyInstaller exe 는 DPI-aware 매니페스트가 없음 -> 좌표계를 python.exe 와 동일하게"""
    if not IS_WIN:
        return
    import ctypes
    for fn in (lambda: ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)),
               lambda: ctypes.windll.shcore.SetProcessDpiAwareness(2),
               lambda: ctypes.windll.user32.SetProcessDPIAware()):
        try:
            fn()
            return
        except Exception:
            continue


def _check_mac_permissions() -> str:
    """macOS 권한 확인. 없으면 pynput 리스너가 조용히 종료되므로 명시적으로 알림. 부족 항목 문자열 반환."""
    if not IS_MAC:
        return ""
    missing = []
    try:
        import ApplicationServices as AS
        if not AS.AXIsProcessTrustedWithOptions({"AXTrustedCheckOptionPrompt": True}):
            missing.append("손쉬운 사용")
    except Exception as e:
        log.warning("AX check: %s", e)
    try:
        import Quartz
        if hasattr(Quartz, "CGPreflightListenEventAccess") and not Quartz.CGPreflightListenEventAccess():
            Quartz.CGRequestListenEventAccess()
            missing.append("입력 모니터링")
    except Exception as e:
        log.warning("ListenEvent check: %s", e)
    if missing:
        log.error("권한 필요: %s -> 시스템 설정 > 개인정보 보호 및 보안 에서 허용 후 재시작", ", ".join(missing))
    return ", ".join(missing)


def _icon(color):
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((6, 14, 58, 50), radius=12, fill=color)
    d.ellipse((24, 22, 40, 42), fill=(255, 255, 255, 255))
    return img


def _open(path):
    cmd = ["open", "-t", path] if IS_MAC else ["notepad.exe", path] if IS_WIN else ["xdg-open", path]
    subprocess.Popen(cmd)


def main():
    cfg = config.load()
    logcfg.setup(logging.DEBUG if cfg["verbose"] else logging.INFO, config.log_path())
    log.info("==== MouseBridge %s start ====", __version__)
    log.info("config %s: %s", config.config_path(), cfg)
    _set_dpi_aware()
    perm_missing = _check_mac_permissions()

    from .bridge import Bridge           # 로깅/DPI 설정 후 import
    from .net import run_forever

    bridge = Bridge(config.peer_edge(cfg), cfg["swap_cmd_ctrl"], cfg["hangul_mac"], own_capture=False)
    bridge.capture.start()               # 메인 스레드에서 훅 설치
    stop = threading.Event()
    state = {"status": "시작 중", "icon": None}

    def set_status(msg):
        if perm_missing:
            msg = f"{msg} / 권한 필요: {perm_missing}"
        state["status"] = msg
        if state["icon"]:
            ok = msg.startswith("연결됨") and not perm_missing
            state["icon"].title = f"MouseBridge - {msg}"
            state["icon"].icon = _icon((40, 160, 90, 255) if ok else (120, 120, 120, 255))

    t = threading.Thread(target=run_forever,
                         args=(bridge, cfg["role"], cfg["peer_host"], cfg["port"], stop, set_status),
                         daemon=True)
    t.start()

    try:
        import pystray
    except Exception:
        log.warning("pystray unavailable; headless mode")
        try:
            t.join()
        except KeyboardInterrupt:
            stop.set()
        return

    menu = pystray.Menu(
        pystray.MenuItem(lambda _: state["status"], None, enabled=False),
        pystray.MenuItem(lambda _: f"역할: {cfg['role']} · 내 위치: {cfg['my_position']}", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("설정 파일 열기", lambda i, _: _open(config.config_path())),
        pystray.MenuItem("로그 열기", lambda i, _: _open(config.log_path())),
        pystray.MenuItem("종료", lambda i, _: (stop.set(), i.stop())),
    )
    icon = pystray.Icon("MouseBridge", _icon((120, 120, 120, 255)), "MouseBridge", menu)
    state["icon"] = icon
    icon.run()
    bridge.capture.stop()


if __name__ == "__main__":
    main()
