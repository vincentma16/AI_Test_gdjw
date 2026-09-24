"""日志配置：读取 config/logging.conf。"""
from __future__ import annotations

import logging
import logging.config
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_LOGGING_CONF = _PROJECT_ROOT / "config" / "logging.conf"


def _setup() -> logging.Logger:
    if _LOGGING_CONF.exists():
        logging.config.fileConfig(_LOGGING_CONF, disable_existing_loggers=False)
    return logging.getLogger("ui-automation")


logger = _setup()
