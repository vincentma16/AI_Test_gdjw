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

from common.auth import apply_auth, apply_biz_auth, login
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
        f"业务服务={','.join(config.services.keys())}\n"
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
    """全局请求句柄，session 级复用（不自动鉴权）。"""
    handler = RequestHandler(config)
    yield handler
    handler.close()


@pytest.fixture(scope="session")
def auth_api(config) -> RequestHandler:
    """带鉴权的请求句柄：独立 session，登录后自动注入 token 到请求头与查询参数（auth 接口）。"""
    handler = RequestHandler(config)
    token = login(handler, config.auth)
    apply_auth(handler, config.auth, token)
    yield handler
    handler.close()


@pytest.fixture(scope="session")
def biz_api(config) -> RequestHandler:
    """带业务鉴权的请求句柄：登录 + 多头鉴权 + 岗位头（svc-main/svc-deal/svc-bill 业务接口）。

    用法：biz_api.post(config.service_url("svc-main") + "/api/client/...", ...)
    """
    handler = RequestHandler(config)
    token = login(handler, config.auth)
    apply_biz_auth(handler, config, token)
    yield handler
    handler.close()
