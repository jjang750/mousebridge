"""mDNS(_mousebridge._tcp) 로 상대 PC 자동 탐색."""
import socket
import time

SERVICE = "_mousebridge._tcp.local."


def _local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


class Advertiser:
    """대기측: 서비스 광고"""
    def __init__(self, port: int, name: str):
        from zeroconf import ServiceInfo, Zeroconf
        self.zc = Zeroconf()
        self.info = ServiceInfo(
            SERVICE, f"{name}.{SERVICE}", addresses=[socket.inet_aton(_local_ip())],
            port=port, properties={"v": "1"}, server=f"{name}.local.")
        self.zc.register_service(self.info)

    def close(self):
        try:
            self.zc.unregister_service(self.info)
            self.zc.close()
        except Exception:
            pass


def find_peer(timeout: float = 5.0):
    """접속측: (host, port) 또는 None"""
    from zeroconf import ServiceBrowser, Zeroconf
    found = {}

    class L:
        def add_service(self, zc, t, name):
            info = zc.get_service_info(t, name)
            if info and info.addresses:
                found["peer"] = (socket.inet_ntoa(info.addresses[0]), info.port)
        def update_service(self, *a): pass
        def remove_service(self, *a): pass

    zc = Zeroconf()
    ServiceBrowser(zc, SERVICE, L())
    t0 = time.time()
    try:
        while time.time() - t0 < timeout and "peer" not in found:
            time.sleep(0.2)
    finally:
        zc.close()
    return found.get("peer")
