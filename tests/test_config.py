import json

from bridge import config


def test_defaults_and_legacy_edge(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "config_dir", lambda: str(tmp_path))
    cfg = config.load()                                   # 파일 없음 -> 기본값 생성
    assert cfg["my_position"] in ("left", "right") and (tmp_path / "config.json").exists()

    (tmp_path / "config.json").write_text(json.dumps({"edge": "right", "port": 1}), encoding="utf-8")
    cfg = config.load()
    assert cfg["my_position"] == "left" and cfg["port"] == 1   # edge=right(상대 오른쪽) -> 내 위치 left
    assert config.peer_edge(cfg) == "right"
