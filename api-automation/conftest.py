"""全局 pytest fixture。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Windows 控制台切到 UTF-8，避免中文日志乱码
if sys.platform == "win32":
    os.system("chcp 65001 > nul")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import allure
import pytest

from common.config import Config
from common.logger import logger
from common.request_handler import RequestHandler

_PROJECT_ROOT = Path(__file__).resolve().parent


def pytest_addoption(parser):
    parser.addoption(
        "--env",
        default="dev",
        choices=["dev", "uat", "sit", "prod"],
        help="运行环境: dev / uat / sit / prod",
    )


@pytest.fixture(autouse=True)
def _allure_epic():
    """自动为所有用例打 epic 标签，与 UI 自动化报告区分。"""
    allure.dynamic.epic("接口自动化")


@pytest.fixture(scope="session", autouse=True)
def _allure_environment(config):
    """写入 Allure 环境信息（--clean-alluredir 会清空目录，需在会话开始时写入）。"""
    results_dir = _PROJECT_ROOT / "reports" / "allure-results"
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "environment.properties").write_text(
        f"测试类型=接口自动化\n"
        f"项目=api-automation\n"
        f"环境={config.env}\n"
        f"BaseURL={config.base_url}\n"
        f"超时={config.timeout}s\n",
        encoding="utf-8",
    )


@pytest.fixture(scope="session")
def config(request) -> Config:
    env = request.config.getoption("--env")
    cfg = Config.load(env=env)
    logger.info("已加载环境: env=%s base_url=%s", env, cfg.base_url)
    return cfg


@pytest.fixture(scope="session")
def api(config) -> RequestHandler:
    """全局请求句柄，session 级复用。

    需要鉴权的系统：参照 config/config.yaml 里的 auth 注释补充配置，
    再在各自的 conftest 或用例里做一次登录并注入请求头。
    """
    handler = RequestHandler(config)
    yield handler
    handler.close()
