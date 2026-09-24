"""配置加载：读取 config/config.yaml，环境变量覆盖敏感项。"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
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
    timeout: float
    retry: int
    auth: dict = field(default_factory=dict)
    services: dict = field(default_factory=dict)

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
        # 环境变量优先覆盖 base_url（约定键名：<ENV>_BASE_URL，全大写）
        base_url = os.environ.get(f"{env.upper()}_BASE_URL") or section.get("base_url")
        if not base_url:
            raise ValueError(f"环境 {env} 未配置 base_url")
        return cls(
            env=env,
            base_url=base_url.rstrip("/"),
            timeout=float(section.get("timeout", defaults.get("timeout", 10))),
            retry=int(section.get("retry", defaults.get("retry", 0))),
            auth=raw.get("auth", {}) or {},
            services=section.get("services", {}) or {},
        )

    def service_url(self, name: str) -> str:
        """返回指定服务的完整 base_url（如 svc-main -> https://sit.example.com/svc-main）。"""
        url = self.services.get(name)
        if not url:
            raise ValueError(f"未配置服务: {name}，可选: {list(self.services.keys())}")
        return url.rstrip("/")
