"""统一日志配置。"""
import logging
import logging.config
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_LOG_CONF = _PROJECT_ROOT / "config" / "logging.conf"

if _LOG_CONF.exists():
    logging.config.fileConfig(_LOG_CONF, disable_existing_loggers=False)

logger = logging.getLogger("api-automation")
