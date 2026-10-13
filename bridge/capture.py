"""입력 캡처 레이어 (pynput + OS 훅). Windows / macOS 전용.

LOCAL 모드 : on_move(x, y) 만 전달(가장자리 감지용).
REMOTE 모드: OS 훅에서 직접 변환해 콜백을 호출하고, 로컬 전달은 차단.
  * macOS  : darwin_intercept -> 델타/키코드 추출 후 None 반환
  * Windows: win32_event_filter -> 변환 후 suppress_event()
             (suppress_event 는 예외로 빠져나가므로 pynput 콜백은 호출되지 않음)
"""
import ctypes
import logging
import sys

from pynput import keyboard, mouse

from . import keymap

log = logging.getLogger("capture")
IS_WIN = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"

if IS_MAC:
    import Quartz
    _MOVE_TYPES = {Quartz.kCGEventMouseMoved, Quartz.kCGEventLeftMouseDragged,
                   Quartz.kCGEventRightMouseDragged, Quartz.kCGEventOtherMouseDragged}
elif IS_WIN:
    from ctypes import wintypes
    _user32 = ctypes.windll.user32
    _WM_MOUSEMOVE = 0x0200

    def _cursor_pos():
        pt = wintypes.POINT()
        _user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y
else:
    raise ImportError("MouseBridge supports Windows and macOS only")


class Capture:
    """콜백: on_move(x,y) on_delta(dx,dy) on_button(name,pressed) on_wheel(dx,dy) on_key(hid,pressed)
    is_remote(): True 면 로컬 입력 차단 + 원격 전송"""

    def __init__(self, on_move, on_delta, on_button, on_wheel, on_key, is_remote):
        self.on_move, self.on_delta = on_move, on_delta
        self.on_button, self.on_wheel, self.on_key = on_button, on_wheel, on_key
        self.is_remote = is_remote
        self._mouse = self._kbd = None

    # ---------- 공통 (LOCAL 모드 전용 콜백) ----------
    def _m_move(self, x, y):
        if not self.is_remote():
            self.on_move(int(x), int(y))

    # ---------- macOS ----------
    def _m_darwin(self, event_type, event):
        if not self.is_remote():
            return event
        if event_type in _MOVE_TYPES:
            dx = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGMouseEventDeltaX)
            dy = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGMouseEventDeltaY)
            if dx or dy:
                self.on_delta(int(dx), int(dy))
        elif event_type in (Quartz.kCGEventLeftMouseDown, Quartz.kCGEventLeftMouseUp):
            self.on_button("left", event_type == Quartz.kCGEventLeftMouseDown)
        elif event_type in (Quartz.kCGEventRightMouseDown, Quartz.kCGEventRightMouseUp):
            self.on_button("right", event_type == Quartz.kCGEventRightMouseDown)
        elif event_type in (Quartz.kCGEventOtherMouseDown, Quartz.kCGEventOtherMouseUp):
            self.on_button("middle", event_type == Quartz.kCGEventOtherMouseDown)
        elif event_type == Quartz.kCGEventScrollWheel:
            dy = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGScrollWheelEventDeltaAxis1)
            dx = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGScrollWheelEventDeltaAxis2)
            if dx or dy:
                self.on_wheel(int(dx), int(dy))
        return None

    def _k_darwin(self, event_type, event):
        if not self.is_remote():
            return event
        try:
            kc = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
            hid = keymap.mac_to_hid(kc)
            if hid is None:
                return None
            if event_type == Quartz.kCGEventFlagsChanged:
                mask = keymap.MAC_MOD_MASK.get(kc)
                if kc == 0x39:                         # caps lock: 토글 상태 -> press+release
                    self.on_key(hid, True)
                    self.on_key(hid, False)
                elif mask:
                    self.on_key(hid, bool(Quartz.CGEventGetFlags(event) & mask))
            else:
                self.on_key(hid, event_type == Quartz.kCGEventKeyDown)
        except Exception:
            log.exception("mac key intercept")
        return None

    # ---------- Windows ----------
    def _m_win(self, msg, data):
        if not self.is_remote():
            return
        L = self._mouse
        try:
            if msg == _WM_MOUSEMOVE:
                cx, cy = _cursor_pos()
                dx, dy = data.pt.x - cx, data.pt.y - cy
                if dx or dy:
                    self.on_delta(dx, dy)
            elif msg in L.CLICK_BUTTONS:
                btn, pressed = L.CLICK_BUTTONS[msg]
                self.on_button(btn.name, pressed)
            elif msg in L.X_BUTTONS:
                btn, pressed = L.X_BUTTONS[msg][data.mouseData >> 16]
                self.on_button(btn.name, pressed)
            elif msg in L.SCROLL_BUTTONS:
                mx, my = L.SCROLL_BUTTONS[msg]
                dd = ctypes.c_short(data.mouseData >> 16).value // 120
                self.on_wheel(dd * mx, dd * my)
        except Exception:
            log.exception("win mouse filter")
        L.suppress_event()

    def _k_win(self, msg, data):
        if not self.is_remote():
            return
        L = self._kbd
        try:
            hid = keymap.win_to_hid(data.vkCode, bool(data.flags & 0x01))   # LLKHF_EXTENDED
            if hid is not None:
                if msg in L._PRESS_MESSAGES:
                    self.on_key(hid, True)
                elif msg in L._RELEASE_MESSAGES:
                    self.on_key(hid, False)
        except Exception:
            log.exception("win key filter")
        L.suppress_event()

    # ---------- lifecycle ----------
    def start(self):
        if IS_WIN:
            mkw, kkw = {"win32_event_filter": self._m_win}, {"win32_event_filter": self._k_win}
        else:
            mkw, kkw = {"darwin_intercept": self._m_darwin}, {"darwin_intercept": self._k_darwin}
        self._mouse = mouse.Listener(on_move=self._m_move, **mkw)
        self._kbd = keyboard.Listener(**kkw)
        self._mouse.start()
        self._kbd.start()
        log.info("capture started (%s)", "windows" if IS_WIN else "macos")

    def stop(self):
        for l in (self._mouse, self._kbd):
            if l:
                l.stop()
