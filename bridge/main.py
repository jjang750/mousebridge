"""CLI 진입점.
  python -m bridge.main --listen --my-position left
  python -m bridge.main --connect [HOST] --my-position right
"""
import argparse
import logging

from . import config, log as logcfg
from .bridge import Bridge
from .net import run_forever


def main():
    ap = argparse.ArgumentParser(description="MouseBridge CLI")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--listen", action="store_true", help="연결 대기")
    g.add_argument("--connect", metavar="HOST", nargs="?", const="", help="상대 PC 주소(생략 시 mDNS 탐색)")
    ap.add_argument("--my-position", choices=["left", "right", "top", "bottom"],
                    default=config.DEFAULTS["my_position"], help="내 PC 의 위치")
    ap.add_argument("--port", type=int, default=24800)
    ap.add_argument("--swap-cmd-ctrl", action="store_true", help="수신 시 Ctrl<->Cmd 교환")
    ap.add_argument("--hangul-mac", choices=["kana", "capslock", "ctrl-space", "cmd-space"], default="kana")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()

    logcfg.setup(logging.DEBUG if a.verbose else logging.INFO)
    bridge = Bridge(config.peer_edge({"my_position": a.my_position}), a.swap_cmd_ctrl, a.hangul_mac)
    try:
        run_forever(bridge, "listen" if a.listen else "connect", a.connect or "", a.port)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
