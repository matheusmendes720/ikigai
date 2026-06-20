"""Structured logging for life OS. File + optional JSON."""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .config import load_config


def _ensure_log_dir(cfg: Optional[Any] = None) -> Path:
    cfg = cfg or load_config()
    cfg.ensure_dirs()
    return cfg.log_dir


def get_logger(
    name: str = "life",
    level: Optional[str] = None,
    log_dir: Optional[Path] = None,
    json_format: Optional[bool] = None,
) -> logging.Logger:
    """Return a configured logger. Uses life config if args not provided."""
    cfg = load_config()
    level = level or cfg.log_level
    log_dir = log_dir or cfg.log_dir
    json_format = json_format if json_format is not None else cfg.log_json

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    class PlainFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            t = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            return f"{t} [{record.levelname}] {record.name}: {record.getMessage()}"

    class JsonFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            import json
            t = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            d = {
                "time": t,
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
            if record.exc_info:
                d["exc"] = self.formatException(record.exc_info)
            return json.dumps(d, ensure_ascii=False)

    fmt = JsonFormatter() if json_format else PlainFormatter()
    h_console = logging.StreamHandler(sys.stderr)
    h_console.setFormatter(fmt)
    logger.addHandler(h_console)

    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "life.log"
    try:
        h_file = logging.FileHandler(log_file, encoding="utf-8")
        h_file.setFormatter(fmt)
        logger.addHandler(h_file)
    except OSError:
        pass

    return logger


# Module-level logger for convenience
def log() -> logging.Logger:
    return get_logger()
