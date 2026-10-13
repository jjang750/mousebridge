"""로깅 설정. CLI 는 콘솔, 앱은 파일(+콘솔이 있으면 콘솔)."""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

FMT = "%(asctime)s %(levelname).1s %(name)s: %(message)s"


def setup(level=logging.INFO, file_path: str | None = None) -> logging.Logger:
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    if sys.stdout is not None and hasattr(sys.stdout, "write"):
        root.addHandler(logging.StreamHandler(sys.stdout))
    if file_path:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        root.addHandler(RotatingFileHandler(file_path, maxBytes=2_000_000, backupCount=2, encoding="utf-8"))
    for h in root.handlers:
        h.setFormatter(logging.Formatter(FMT, "%H:%M:%S"))
    # windowed 빌드에서 stdout=None 이면 print 가 죽지 않게
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")
    return root
