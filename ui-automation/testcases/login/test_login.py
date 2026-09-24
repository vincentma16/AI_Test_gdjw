"""登录 UI 测试。

- test_real_login：真实登录示例系统（sit 环境），账号走 .env，预期值走 data/login.yaml。
- test_login：本地 fixture 框架验证（local 环境），数据驱动。
所有输入值、预期断言值（URL片段/token key/超时）均来自 data/login.yaml，
用例只做调用与断言，不硬编码任何业务数据。
"""
from __future__ import annotations

import os
from pathlib import Path

import allure
import pytest
import yaml

from common.assert_util import assert_contains_text, assert_visible
from pages.login_page import LoginPage

# 用例在 testcases/<module>/ 下，数据在项目根 data/ 下，故向上 3 级定位项目根
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DATA_FILE = _PROJECT_ROOT / "data" / "login.yaml"

with open(_DATA_FILE, "r", encoding="utf-8") as _f:
    _DATA = yaml.safe_load(_f)

_CASES = _DATA["cases"]
_REAL_LOGIN = _DATA["real_login"]


@pytest.mark.login
def test_real_login(page, config):
    """验证码授权登录示例系统，进入工作台（真实环境）。"""
    if config.env == "local":
        pytest.skip("真实登录用例不在 local 环境运行")

    phone = os.environ.get("TEST_PHONE")
    code = os.environ.get("TEST_CODE")
    assert phone and code, "请在 .env 中配置 TEST_PHONE 和 TEST_CODE"

    allure.dynamic.feature(_REAL_LOGIN["feature"])
    allure.dynamic.story(_REAL_LOGIN["story"])
    allure.dynamic.title(_REAL_LOGIN["title"])

    login_page = LoginPage(page)
    exp = _REAL_LOGIN["expect"]

    with allure.step("打开登录页（web 入口，自动重定向 sso）"):
        login_page.open(config.login_url)
        allure.attach(page.url, name="登录页URL", attachment_type=allure.attachment_type.TEXT)

    with allure.step("验证码授权登录"):
        login_page.login(phone, code)
        allure.attach(
            f"手机号: {phone}", name="登录信息", attachment_type=allure.attachment_type.TEXT
        )

    with allure.step("等待并断言进入工作台"):
        assert login_page.wait_for_login_success(timeout=exp["login_timeout"]), "登录后未进入工作台"
        assert exp["url_contains"] in page.url, (
            f"URL 不含 {exp['url_contains']}, 实际: {page.url}"
        )
        assert_visible(login_page.workbench_menu, "工作台菜单")
        token = page.evaluate(f"() => localStorage.getItem({exp['token_key']!r})")
        assert token, f"localStorage 未获取到 {exp['token_key']}"
        allure.attach(token[:20] + "...", name="token", attachment_type=allure.attachment_type.TEXT)

    login_page.screenshot("工作台")


@pytest.mark.login
@pytest.mark.parametrize(
    "case",
    _CASES,
    ids=[c["id"] for c in _CASES],
)
def test_login(page, config, case):
    """本地 fixture 框架验证用例（数据驱动）。"""
    if config.env != "local":
        pytest.skip("本地 fixture 用例仅在 local 环境运行")

    allure.dynamic.feature(case["feature"])
    allure.dynamic.story(case["story"])
    allure.dynamic.title(f'{case["id"]} {case["name"]}')

    login_page = LoginPage(page)

    with allure.step("打开登录页"):
        login_page.open(config.login_url)

    req = case["request"]
    with allure.step("执行登录操作"):
        login_page.login(req["phone"], req["code"])

    with allure.step("断言登录结果"):
        expect = case["expect"]
        if "success_text" in expect:
            assert_visible(login_page.success_msg, "成功提示")
            assert_contains_text(login_page.success_msg, expect["success_text"], "成功提示文本")
        elif "error_text" in expect:
            error = page.locator(f"text={expect['error_text']}").first
            assert_visible(error, "错误提示")

    login_page.screenshot("登录结果")
