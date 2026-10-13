"""역할 상태머신과 프레임 처리.

LOCAL      : 내 입력이 내 화면을 제어 (기본)
REMOTE     : 내 입력을 상대에게 전송, 로컬 입력은 훅에서 차단
CONTROLLED : 상대 입력을 내 화면에 주입
"""
import logging
import platform
import socket
import threading
import time

from screeninfo import get_monitors

from . import proto
from .capture import Capture
from .inject import Inject

log = logging.getLogger("bridge")
LOCAL, REMOTE, CONTROLLED = "LOCAL", "REMOTE", "CONTROLLED"
_H = (proto.EDGE_LEFT, proto.EDGE_RIGHT)   # 수평 가장자리


def screen_bounds():
    """모든 모니터를 포함하는 가상 화면 (x, y, w, h)"""
    ms = get_monitors()
    x0, y0 = min(m.x for m in ms), min(m.y for m in ms)
    x1, y1 = max(m.x + m.width for m in ms), max(m.y + m.height for m in ms)
    return x0, y0, x1 - x0, y1 - y0


class Bridge:
    def __init__(self, peer_edge: str, swap_cmd_ctrl=False, hangul_mac="kana", own_capture=True):
        """peer_edge: 상대 PC 가 있는 방향(left/right/top/bottom).
        own_capture: False 면 외부(app)가 캡처 start/stop 을 관리."""
        self.edge = proto.EDGE_NAME[peer_edge]
        self.sx, self.sy, self.sw, self.sh = screen_bounds()
        self.state = LOCAL
        self.sock = None
        self._lock = threading.Lock()
        self.peer = {"w": 0, "h": 0, "name": "?"}
        self.inject = Inject(swap_cmd_ctrl, hangul_mac)
        self.capture = Capture(self.on_move, self.on_delta, self.on_button, self.on_wheel,
                               self.on_key, lambda: self.state == REMOTE)
        self.own_capture = own_capture
        self.rx = self.ry = 0           # REMOTE 중 상대 화면 위 가상 커서
        log.info("screen x=%d y=%d %dx%d, peer edge=%s", self.sx, self.sy, self.sw, self.sh, peer_edge)

    # ---------------- network ----------------
    def send(self, data: bytes):
        with self._lock:
            s = self.sock
        if s is None:
            return
        try:
            s.sendall(data)
        except OSError as e:
            log.warning("send: %s", e)

    def run(self, sock: socket.socket):
        """연결 하나를 끝날 때까지 처리 (블로킹)."""
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        with self._lock:
            self.sock = sock
        self.send(proto.hello(self.sw, self.sh, platform.node()))
        if self.own_capture:
            self.capture.start()
        threading.Thread(target=self._pinger, args=(sock,), daemon=True).start()
        try:
            while True:
                self.handle(*proto.read_frame(sock))
        except (ConnectionError, OSError) as e:
            log.info("disconnected: %s", e)
        finally:
            with self._lock:
                self.sock = None
            if self.own_capture:
                self.capture.stop()
            self.inject.release_all()
            self.state = LOCAL

    def _pinger(self, sock):
        while self.sock is sock:
            self.send(proto.ping(int(time.time() * 1000)))
            time.sleep(5)

    # ---------------- incoming ----------------
    def handle(self, t, d):
        if t == proto.HELLO:
            self.peer = d
            log.info("peer=%s screen=%dx%d", d["name"], d["w"], d["h"])
        elif t == proto.ENTER:
            self._enter_controlled(d["edge"], d["ratio"])
        elif t == proto.LEAVE:
            self.inject.release_all()
            self.state = LOCAL
            log.debug("-> LOCAL (peer left)")
        elif self.state == CONTROLLED:
            if t == proto.MOVE:
                self.inject.move(d["dx"], d["dy"])
            elif t == proto.BUTTON:
                self.inject.button(d["btn"], d["pressed"])
            elif t == proto.WHEEL:
                self.inject.wheel(d["dx"], d["dy"])
            elif t == proto.KEY:
                self.inject.key(d["hid"], d["pressed"])
        if t == proto.PING:
            self.send(proto.pong(d["ts"]))
        elif t == proto.PONG:
            log.debug("rtt=%dms", int(time.time() * 1000) - d["ts"])

    def _enter_controlled(self, enter_edge: int, ratio: float):
        ratio = max(0.0, min(1.0, ratio))
        if enter_edge in _H:
            x = self.sx + (1 if enter_edge == proto.EDGE_LEFT else self.sw - 2)
            y = self.sy + int(ratio * (self.sh - 1))
        else:
            x = self.sx + int(ratio * (self.sw - 1))
            y = self.sy + (1 if enter_edge == proto.EDGE_TOP else self.sh - 2)
        self.state = CONTROLLED
        self.inject.set_pos(x, y)
        log.debug("-> CONTROLLED at (%d,%d)", x, y)

    # ---------------- local input ----------------
    def on_move(self, x, y):
        if self.state != LOCAL or self.peer["w"] == 0:
            return
        e = self.edge
        hit = ((e == proto.EDGE_RIGHT and x >= self.sx + self.sw - 1) or
               (e == proto.EDGE_LEFT and x <= self.sx) or
               (e == proto.EDGE_BOTTOM and y >= self.sy + self.sh - 1) or
               (e == proto.EDGE_TOP and y <= self.sy))
        if not hit:
            return
        pw, ph = self.peer["w"], self.peer["h"]
        if e in _H:
            ratio = (y - self.sy) / max(1, self.sh - 1)
            self.rx, self.ry = (0 if e == proto.EDGE_RIGHT else pw - 1), int(ratio * (ph - 1))
        else:
            ratio = (x - self.sx) / max(1, self.sw - 1)
            self.rx, self.ry = int(ratio * (pw - 1)), (0 if e == proto.EDGE_BOTTOM else ph - 1)
        self.state = REMOTE
        self.send(proto.enter(proto.OPPOSITE[e], ratio))
        log.debug("-> REMOTE (ratio=%.2f)", ratio)

    def on_delta(self, dx, dy):
        if self.state != REMOTE:
            return
        self.send(proto.move(dx, dy))
        pw, ph = self.peer["w"], self.peer["h"]
        self.rx += dx
        self.ry += dy
        e = self.edge
        back = ((e == proto.EDGE_RIGHT and self.rx < 0) or (e == proto.EDGE_LEFT and self.rx >= pw) or
                (e == proto.EDGE_BOTTOM and self.ry < 0) or (e == proto.EDGE_TOP and self.ry >= ph))
        # 가상 커서를 상대 화면 안으로 유지 (복귀 축은 제외)
        if e in _H:
            self.ry = max(0, min(ph - 1, self.ry))
        else:
            self.rx = max(0, min(pw - 1, self.rx))
        if not back:
            return
        self.send(proto.leave())
        self.state = LOCAL
        if e in _H:
            x = self.sx + (self.sw - 3 if e == proto.EDGE_RIGHT else 2)
            y = self.sy + int(self.ry / max(1, ph - 1) * (self.sh - 1))
        else:
            x = self.sx + int(self.rx / max(1, pw - 1) * (self.sw - 1))
            y = self.sy + (self.sh - 3 if e == proto.EDGE_BOTTOM else 2)
        self.inject.set_pos(x, y)
        log.debug("-> LOCAL (returned)")

    def on_button(self, name, pressed):
        self.send(proto.button(name, pressed))

    def on_wheel(self, dx, dy):
        self.send(proto.wheel(dx, dy))

    def on_key(self, hid, pressed):
        self.send(proto.key(hid, pressed))
