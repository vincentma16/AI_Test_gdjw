"""全局 pytest fixture。"""
from __future__ import annotations

import os
from pathlib import Path

import allure
import pytest
from playwright.sync_api import BrowserContext, Page

from common.browser import BrowserFactory
from common.config import Config
from common.logger import logger

_PROJECT_ROOT = Path(__file__).resolve().parent
# 登录态含真实凭证，默认不落宿主机：容器内由 AUTH_STATE_FILE 指向 /tmp，
# 随容器销毁；需要留痕时显式设置该变量指向可写路径。
_STATE_FILE = Path(
    os.environ.get("AUTH_STATE_FILE")
    or (_PROJECT_ROOT / "reports" / ".auth_state.json")
)


def pytest_addoption(parser):
    parser.addoption(
        "--env",
        default="local",
        choices=["local", "dev", "uat", "sit", "prod"],
        help="运行环境: local / dev / uat / sit / prod",
    )
    parser.addoption(
        "--headed",
        action="store_true",
        default=False,
        help="有头模式运行浏览器（覆盖 headless），用于调试",
    )


@pytest.fixture(autouse=True)
def _allure_epic():
    """自动为所有用例打 epic 标签，与接口自动化报告区分。"""
    allure.dynamic.epic("UI自动化")


@pytest.fixture(scope="session", autouse=True)
def _allure_environment(config):
    """写入 Allure 环境信息（--clean-alluredir 会清空目录，需在会话开始时写入）。"""
    results_dir = _PROJECT_ROOT / "reports" / "allure-results"
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "environment.properties").write_text(
        f"测试类型=UI自动化\n"
        f"项目=ui-automation\n"
        f"环境={config.env}\n"
        f"首页={config.home_url}\n"
        f"浏览器={config.browser}\n"
        f"Headless={config.headless}\n",
        encoding="utf-8",
    )


@pytest.fixture(scope="session")
def config(request) -> Config:
    env = request.config.getoption("--env")
    cfg = Config.load(env=env)
    if request.config.getoption("--headed"):
        cfg.headless = False
        logger.info("已启用有头模式（--headed），覆盖 headless 配置")
    logger.info(
        "已加载环境: env=%s home_url=%s headless=%s", env, cfg.home_url, cfg.headless
    )
    return cfg


@pytest.fixture(scope="session")
def browser_factory(config) -> BrowserFactory:
    factory = BrowserFactory(config)
    yield factory
    factory.close()


@pytest.fixture(scope="function")
def context(browser_factory) -> BrowserContext:
    ctx = browser_factory.new_context()
    yield ctx
    ctx.close()


@pytest.fixture(scope="function")
def page(context) -> Page:
    p = context.new_page()
    yield p
    p.close()


@pytest.fixture(scope="session")
def stored_state(config) -> str | None:
    """已登录状态文件路径，供需要登录态的用例复用（避免每条用例重复登录）。

    当前为空实现：local 环境跑本地 fixture，不需要登录态。
    接入真实系统后，在这里补一次登录并保存 storage_state，示例：

        ctx = browser_factory.new_context()
        page = ctx.new_page()
        # ... 执行登录 ...
        ctx.storage_state(path=str(_STATE_FILE))
        return str(_STATE_FILE)
    """
    if config.env == "local":
        return None
    logger.info("未配置登录流程，直接以未登录状态执行（env=%s）", config.env)
    return None


# --------------------------------------------------------------------------- #
# 失败自动截图：用例 call 阶段失败时，自动截图并附加到 Allure 报告，方便排查。
# --------------------------------------------------------------------------- #
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        _attach_failure_artifacts(item)


def _attach_failure_artifacts(item):
    """用例失败时自动截图、保存URL与页面提示，附加到 Allure 报告。"""
    page = None
    for name in ("app_page", "page"):
        p = item.funcargs.get(name)
        if p is not None:
            page = p
            break
    if page is None:
        return
    try:
        png = page.screenshot()
        allure.attach(png, name="失败截图", attachment_type=allure.attachment_type.PNG)
    except Exception as e:
        logger.warning("失败截图失败: %s", e)
    try:
        allure.attach(
            page.url, name="失败时URL", attachment_type=allure.attachment_type.TEXT
        )
    except Exception:
        pass
