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
from pages.login_page import LoginPage

_PROJECT_ROOT = Path(__file__).resolve().parent
_STATE_FILE = _PROJECT_ROOT / "reports" / ".auth_state.json"


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
        f"BaseURL={config.base_url}\n"
        f"登录页={config.login_url}\n"
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
        "已加载环境: env=%s login_url=%s headless=%s", env, cfg.login_url, cfg.headless
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
def auth_state(browser_factory, config) -> str | None:
    """登录一次，保存 storage_state 供后续业务用例复用（避免每个用例重复登录）。

    local 环境使用本地 HTML fixture，无需真实登录。
    """
    if config.env == "local":
        return None
    phone = os.environ.get("TEST_PHONE")
    code = os.environ.get("TEST_CODE")
    assert phone and code, "请在 .env 中配置 TEST_PHONE 和 TEST_CODE"

    ctx = browser_factory.new_context()
    page = ctx.new_page()
    try:
        login_page = LoginPage(page)
        login_page.open(config.login_url)
        login_page.login(phone, code)
        assert login_page.wait_for_login_success(timeout=60000), "登录态获取失败"
        logger.info("登录成功，已保存 storage_state")
    finally:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        ctx.storage_state(path=str(_STATE_FILE))
        ctx.close()
    return str(_STATE_FILE)


@pytest.fixture(scope="function")
def app_page(browser_factory, config, auth_state) -> Page:
    """已登录的业务 page：通过 storage_state 复用登录态，每个用例独立上下文。

    local 环境无真实登录态，业务用例自动跳过。
    """
    if config.env == "local":
        pytest.skip("业务用例需要真实环境，local 环境跳过")
    ctx = browser_factory.new_context(storage_state=auth_state)
    p = ctx.new_page()
    yield p
    ctx.close()


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
    """用例失败时自动截图、保存URL与页面消息，附加到 Allure 报告。"""
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
    try:
        msgs = page.locator(".ant-message-notice-content").all_inner_texts()
        if msgs:
            allure.attach(
                "\n".join(msgs),
                name="失败时页面消息",
                attachment_type=allure.attachment_type.TEXT,
            )
    except Exception:
        pass
