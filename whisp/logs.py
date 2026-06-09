"""Lightweight file logging so we can see which engine/model handled each
dictation (and catch any fallback to local). Logs to the app support dir."""
import logging
from logging.handlers import RotatingFileHandler

from whisp import config

_logger = None


def log_path():
    return config.support_dir() / "whisp.log"


def get_logger():
    global _logger
    if _logger is None:
        lg = logging.getLogger("whisp")
        lg.setLevel(logging.INFO)
        lg.propagate = False
        if not lg.handlers:
            handler = RotatingFileHandler(str(log_path()), maxBytes=1_000_000, backupCount=3)
            handler.setFormatter(logging.Formatter("%(asctime)s  %(message)s"))
            lg.addHandler(handler)
        _logger = lg
    return _logger


def log(message: str) -> None:
    try:
        get_logger().info(message)
    except Exception:
        pass
