"""프레임 프로토콜: [2B length][1B type][payload]  (length = type 1B + payload)"""
import socket
import struct

HELLO, ENTER, MOVE, BUTTON, WHEEL, KEY, LEAVE, PING, PONG = range(1, 10)

EDGE_LEFT, EDGE_RIGHT, EDGE_TOP, EDGE_BOTTOM = 0, 1, 2, 3
EDGE_NAME = {"left": EDGE_LEFT, "right": EDGE_RIGHT, "top": EDGE_TOP, "bottom": EDGE_BOTTOM}
OPPOSITE = {EDGE_LEFT: EDGE_RIGHT, EDGE_RIGHT: EDGE_LEFT, EDGE_TOP: EDGE_BOTTOM, EDGE_BOTTOM: EDGE_TOP}

_I16 = (-32768, 32767)
_I8 = (-128, 127)


def _clamp(v, lo_hi):
    return max(lo_hi[0], min(lo_hi[1], v))


def _frame(t: int, payload: bytes = b"") -> bytes:
    return struct.pack(">HB", len(payload) + 1, t) + payload


def hello(w: int, h: int, name: str) -> bytes:
    return _frame(HELLO, struct.pack(">HH", w, h) + name.encode("utf-8"))


def enter(edge: int, ratio: float) -> bytes:
    return _frame(ENTER, struct.pack(">Bf", edge, ratio))


def move(dx: int, dy: int) -> bytes:
    return _frame(MOVE, struct.pack(">hh", _clamp(dx, _I16), _clamp(dy, _I16)))


def button(btn: str, pressed: bool) -> bytes:
    return _frame(BUTTON, struct.pack(">?", pressed) + btn.encode("utf-8"))


def wheel(dx: int, dy: int) -> bytes:
    return _frame(WHEEL, struct.pack(">bb", _clamp(dx, _I8), _clamp(dy, _I8)))


def key(hid: int, pressed: bool) -> bytes:
    """hid: USB HID Keyboard usage id (keymap.py)"""
    return _frame(KEY, struct.pack(">?H", pressed, hid))


def leave() -> bytes:
    return _frame(LEAVE)


def ping(ts_ms: int) -> bytes:
    return _frame(PING, struct.pack(">Q", ts_ms))


def pong(ts_ms: int) -> bytes:
    return _frame(PONG, struct.pack(">Q", ts_ms))


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("peer closed")
        buf += chunk
    return bytes(buf)


def read_frame(sock: socket.socket):
    """(type, dict) 반환. 연결 종료 시 ConnectionError."""
    (length,) = struct.unpack(">H", _recv_exact(sock, 2))
    body = _recv_exact(sock, length)
    t, p = body[0], body[1:]
    if t == HELLO:
        w, h = struct.unpack(">HH", p[:4])
        return t, {"w": w, "h": h, "name": p[4:].decode("utf-8", "replace")}
    if t == ENTER:
        edge, ratio = struct.unpack(">Bf", p)
        return t, {"edge": edge, "ratio": ratio}
    if t == MOVE:
        dx, dy = struct.unpack(">hh", p)
        return t, {"dx": dx, "dy": dy}
    if t == BUTTON:
        return t, {"btn": p[1:].decode("utf-8"), "pressed": bool(p[0])}
    if t == WHEEL:
        dx, dy = struct.unpack(">bb", p)
        return t, {"dx": dx, "dy": dy}
    if t == KEY:
        pressed, hid = struct.unpack(">?H", p)
        return t, {"hid": hid, "pressed": pressed}
    if t in (PING, PONG):
        return t, {"ts": struct.unpack(">Q", p)[0]}
    if t == LEAVE:
        return t, {}
    return t, {"raw": p}
