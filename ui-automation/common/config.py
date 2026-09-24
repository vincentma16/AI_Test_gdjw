"""配置加载：读取 config/config.yaml，环境变量覆盖敏感项。"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_FILE = _PROJECT_ROOT / "config" / "config.yaml"


@dataclass
class Config:
    """运行时配置。"""

    env: str
    base_url: str
    login_url: str
    timeout: int
    headless: bool
    slow_mo: int
    browser: str  # chromium / firefox / webkit
    channel: str  # chrome / msedge / ""（空则用 Playwright 内置浏览器）

    @classmethod
    def load(cls, env: str) -> "Config":
        load_dotenv(_PROJECT_ROOT / ".env")
        with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        envs = raw.get("environments", {})
        if env not in envs:
            raise ValueError(f"未知环境: {env}，可选: {list(envs.keys())}")
        section = envs[env]
        defaults = raw.get("defaults", {})
        base_url = os.environ.get(f"{env.upper()}_BASE_URL") or section.get("base_url", "")
        login_url = os.environ.get(f"{env.upper()}_LOGIN_URL") or section.get("login_url", "")
        return cls(
            env=env,
            base_url=base_url.rstrip("/"),
            login_url=login_url,
            timeout=int(section.get("timeout", defaults.get("timeout", 30000))),
            headless=str(section.get("headless", defaults.get("headless", False))).lower()
            == "true",
            slow_mo=int(section.get("slow_mo", defaults.get("slow_mo", 0))),
            browser=section.get("browser", defaults.get("browser", "chromium")),
            channel=section.get("channel", defaults.get("channel", "")),
        )
