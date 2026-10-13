"""이벤트 주입 레이어 (pynput Controller). 키는 HID usage -> OS 코드."""
import logging
import sys

from pynput import keyboard, mouse

from . import keymap

log = logging.getLogger("inject")
IS_WIN = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"
_HID_TO_OS = keymap.HID_TO_WIN if IS_WIN else keymap.HID_TO_MAC
_MODS = (keyboard.Key.shift, keyboard.Key.shift_r, keyboard.Key.ctrl, keyboard.Key.ctrl_r,
         keyboard.Key.alt, keyboard.Key.alt_r, keyboard.Key.cmd, keyboard.Key.cmd_r)


class Inject:
    def __init__(self, swap_cmd_ctrl=False, hangul_mac="kana"):
        self.m = mouse.Controller()
        self.k = keyboard.Controller()
        self.swap = swap_cmd_ctrl
        self.hangul_mac = hangul_mac

    # ---------- mouse ----------
    def set_pos(self, x: int, y: int):
        self.m.position = (x, y)

    def move(self, dx: int, dy: int):
        self.m.move(dx, dy)

    def button(self, name: str, pressed: bool):
        btn = getattr(mouse.Button, name, None)
        if btn:
            (self.m.press if pressed else self.m.release)(btn)

    def wheel(self, dx: int, dy: int):
        self.m.scroll(dx, dy)

    # ---------- keyboard ----------
    def _hid_to_key(self, hid: int):
        name = keymap.HID_TO_PYNPUT.get(hid)
        if name:
            return getattr(keyboard.Key, name, None)
        code = _HID_TO_OS.get(hid)
        return keyboard.KeyCode.from_vk(code) if code is not None else None

    def _hangul_mac(self, pressed: bool):
        opt = self.hangul_mac
        if opt == "kana":
            (self.k.press if pressed else self.k.release)(keyboard.KeyCode.from_vk(0x68))
        elif pressed and opt == "capslock":
            self.k.tap(keyboard.Key.caps_lock)
        elif pressed and opt in ("ctrl-space", "cmd-space"):
            mod = keyboard.Key.ctrl if opt == "ctrl-space" else keyboard.Key.cmd
            with self.k.pressed(mod):
                self.k.tap(keyboard.Key.space)

    def key(self, hid: int, pressed: bool):
        if self.swap:
            hid = keymap.SWAP_CMD_CTRL.get(hid, hid)
        if hid == keymap.LANG1 and IS_MAC:
            self._hangul_mac(pressed)
            return
        k = self._hid_to_key(hid)
        if k is None:
            log.debug("unmapped hid 0x%02x", hid)
            return
        try:
            (self.k.press if pressed else self.k.release)(k)
        except Exception as e:
            log.warning("key inject 0x%02x: %s", hid, e)

    def release_all(self):
        """역할 전환/연결 종료 시 눌린 키·버튼 잔상 제거."""
        for b in (mouse.Button.left, mouse.Button.right, mouse.Button.middle):
            try:
                self.m.release(b)
            except Exception:
                pass
        for k in _MODS:
            try:
                self.k.release(k)
            except Exception:
                pass
