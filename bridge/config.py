"""사용자 설정 (config.json).

my_position: 내 PC 의 위치(left/right/top/bottom). 상대는 그 반대편.
기본값: Mac = 왼쪽·대기측, Windows = 오른쪽·접속측.
"""
import json
import logging
import os
import sys

log = logging.getLogger("config")
IS_WIN = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"
APP = "MouseBridge"
_OPPOSITE = {"left": "right", "right": "left", "top": "bottom", "bottom": "top"}

DEFAULTS = {
    "role": "listen" if IS_MAC else "connect",   # listen | connect
    "my_position": "left" if IS_MAC else "right",
    "peer_host": "",                             # 비우면 mDNS 자동 탐색
    "port": 24800,
    "swap_cmd_ctrl": True,
    "hangul_mac": "kana",                        # kana | capslock | ctrl-space | cmd-space
    "verbose": False,
}


def config_dir() -> str:
    if IS_WIN:
        return os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), APP)
    if IS_MAC:
        return os.path.expanduser(f"~/Library/Application Support/{APP}")
    return os.path.expanduser(f"~/.config/{APP.lower()}")


def config_path() -> str:
    return os.path.join(config_dir(), "config.json")


def log_path() -> str:
    return os.path.join(config_dir(), "mousebridge.log")


def peer_edge(cfg: dict) -> str:
    """내 위치 -> 상대가 있는 방향"""
    return _OPPOSITE[cfg["my_position"]]


def load() -> dict:
    cfg = dict(DEFAULTS)
    try:
        with open(config_path(), encoding="utf-8") as f:
            data = json.load(f)
        if "edge" in data and "my_position" not in data:      # 구버전 호환
            data["my_position"] = _OPPOSITE[data.pop("edge")]
        cfg.update({k: v for k, v in data.items() if k in DEFAULTS})
    except FileNotFoundError:
        save(cfg)
    except Exception as e:
        log.warning("config load: %s", e)
    return cfg


def save(cfg: dict):
    os.makedirs(config_dir(), exist_ok=True)
    with open(config_path(), "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
