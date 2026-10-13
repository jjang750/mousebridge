"""연결 관리 루프: 대기(listen) / 접속(connect) + mDNS + 자동 재연결."""
import logging
import platform
import socket
import threading
import time

from . import discovery
from .bridge import Bridge

log = logging.getLogger("net")


def run_forever(bridge: Bridge, role: str, peer_host: str, port: int,
                stop: threading.Event | None = None, status=None):
    """role: listen|connect. peer_host 비면 mDNS 탐색. status(msg) 로 상태 통지."""
    stop = stop or threading.Event()

    def st(msg):
        log.info(msg)
        if status:
            status(msg)

    adv = None
    try:
        while not stop.is_set():
            try:
                if role == "listen":
                    if adv is None:
                        try:
                            adv = discovery.Advertiser(port, platform.node().split(".")[0])
                        except Exception as e:
                            log.warning("mDNS advertise failed: %s", e)
                    conn, addr = _accept(port, stop)
                    if conn is None:
                        break
                    st(f"연결됨 {addr[0]}")
                    bridge.run(conn)
                    st("연결 끊김, 대기 중")
                else:
                    host = peer_host
                    if not host:
                        st("상대 PC 탐색 중(mDNS)")
                        found = discovery.find_peer(5.0)
                        if not found:
                            stop.wait(2)
                            continue
                        host, port = found
                    st(f"접속 중 {host}:{port}")
                    conn = socket.create_connection((host, port), timeout=5)
                    conn.settimeout(None)
                    st(f"연결됨 {host}")
                    bridge.run(conn)
                    st("연결 끊김, 재접속 대기")
            except OSError as e:
                st(f"오류: {e}")
            except Exception:
                log.exception("unexpected")
            stop.wait(2)
    finally:
        if adv:
            adv.close()


def _accept(port: int, stop: threading.Event):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", port))
    srv.listen(1)
    srv.settimeout(1.0)
    log.info("대기 중 :%d", port)
    try:
        while not stop.is_set():
            try:
                return srv.accept()
            except socket.timeout:
                continue
        return None, None
    finally:
        srv.close()
