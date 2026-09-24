"""配置加载：读取 config/config.yaml，环境变量覆盖敏感项。"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_FILE = _PROJECT_ROOT / "config" / "config.yaml"

_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def expand_env(value):
    """递归把字符串里的 ${VAR} 占位替换为环境变量值。

    约定：config.yaml 与用例数据中的敏感值一律写成 ${VAR}，
    真实值放在 .env（已被 .gitignore 忽略）。变量未设置时保留原占位符。
    """
    if isinstance(value, dict):
        return {k: expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [expand_env(v) for v in value]
    if isinstance(value, str):
        return _ENV_PATTERN.sub(lambda m: os.environ.get(m.group(1), m.group(0)), value)
    return value


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
        raw = expand_env(raw)
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
