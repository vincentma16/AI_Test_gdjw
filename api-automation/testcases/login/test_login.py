"""登录接口测试：POST /auth/account/signInByVerifyCode

覆盖正向 / 验证码异常 / 手机号异常 / clientId异常 / 请求体异常 / 安全 共6类场景。
每个用例的 reason 字段记录排查理由，note 字段记录风险提示（附到 Allure 报告）。

实测发现（已纳入用例）：
  - 接口对同一手机号有 5 秒频控，触发时返回 code=-100 "验证码发送太频繁..."
    且被限请求本身会重置倒计时 -> 采用全局共享节流(同一手机号间隔>=6s)从源头避免。
    auth 登录与测试用例共用 login_throttle，互不干扰。
  - 空请求体 {} 的字段校验顺序非确定（mobile/clientId 哪个先报不一定）
    -> 用 contains "不可以为空" 断言，不绑定具体字段名。

接口路径统一由 apis.account.account_api.SIGN_IN_ENDPOINT 提供，用例不硬编码 URL；
请求体作为测试数据存放在 data/login/login.yaml（数据层）。
"""
from __future__ import annotations

import json
from pathlib import Path

import allure
import pytest
import yaml
from dotenv import load_dotenv

from apis.account.account_api import SIGN_IN_ENDPOINT
from common.assert_util import (
    assert_contains,
    assert_jsonpath,
    assert_jsonpath_exists,
    assert_status_code,
)
from common.config import expand_env
from common.throttle import login_throttle

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DATA_FILE = _PROJECT_ROOT / "data" / "login" / "login.yaml"

# 用例数据里的敏感值写成 ${VAR} 占位，真实值来自 .env
load_dotenv(_PROJECT_ROOT / ".env")
with open(_DATA_FILE, "r", encoding="utf-8") as _f:
    _DATA = expand_env(yaml.safe_load(_f))

_CASES = _DATA["cases"]

# severity 字符串 -> Allure 级别
_SEVERITY_MAP = {
    "blocker": allure.severity_level.BLOCKER,
    "critical": allure.severity_level.CRITICAL,
    "normal": allure.severity_level.NORMAL,
    "minor": allure.severity_level.MINOR,
    "trivial": allure.severity_level.TRIVIAL,
}


@pytest.mark.login
@pytest.mark.parametrize(
    "case",
    _CASES,
    ids=[c["id"] for c in _CASES],
)
def test_sign_in_by_verify_code(api, case):
    """验证码登录接口数据驱动用例。"""
    # Allure 元信息
    allure.dynamic.feature(case["feature"])
    allure.dynamic.story(case["story"])
    allure.dynamic.title(f'{case["id"]} {case["name"]}')
    if case.get("severity"):
        allure.dynamic.severity(_SEVERITY_MAP.get(case["severity"], allure.severity_level.NORMAL))
    # 描述=排查理由，让报告里一眼看懂"这个用例在查什么"
    allure.dynamic.description(case.get("reason", ""))
    if case.get("note"):
        allure.attach(case["note"], name="风险提示", attachment_type=allure.attachment_type.TEXT)

    with allure.step(f'发送请求 POST {SIGN_IN_ENDPOINT}'):
        allure.attach(
            json.dumps(case["request"], ensure_ascii=False, indent=2),
            name="请求体",
            attachment_type=allure.attachment_type.JSON,
        )
        # 全局节流：同一手机号间隔 >=6s，避免触发频控
        mobile = case["request"].get("mobile") if isinstance(case["request"], dict) else None
        login_throttle.wait(mobile)
        resp = api.post(SIGN_IN_ENDPOINT, json=case["request"])

    expect = case["expect"]
    with allure.step("断言响应"):
        allure.attach(
            resp.text[:4000],
            name="响应体",
            attachment_type=allure.attachment_type.JSON,
        )
        assert_status_code(resp, expect["status_code"])
        for expr, val in expect.get("jsonpath", {}).items():
            assert_jsonpath(resp, expr, val)
        for expr in expect.get("jsonpath_exists", []):
            assert_jsonpath_exists(resp, expr)
        for text in expect.get("contains", []):
            assert_contains(resp, text)


# ============ 无法用 JSON body 表达的专项场景 ============

@pytest.mark.login
@pytest.mark.security
def test_sign_in_without_content_type(api):
    """排查点：不设置 Content-Type 直接 POST 原始 JSON 字符串。

    实测：服务端反序列化失败，返回通用错误 '出错啦，请稍后重试'。
    说明服务端依赖 Content-Type 判断请求体格式，缺失时未做兜底。
    """
    allure.dynamic.feature("登录")
    allure.dynamic.story("请求体异常-无Content-Type")
    allure.dynamic.title("LOGIN-API-020 无Content-Type登录失败")
    allure.dynamic.severity(allure.severity_level.MINOR)
    allure.dynamic.description("排查点：不设置 Content-Type 直接 POST 原始 JSON 字符串，服务端应能兜底或返回明确错误")

    raw_body = json.dumps(expand_env({
        "mobile": "${TEST_MOBILE}",
        "verifyCode": "${TEST_CODE}",
        "clientId": "${TEST_CLIENT_ID}",
    }), ensure_ascii=False)

    with allure.step("发送不带 Content-Type 的原始 JSON 字符串"):
        allure.attach(raw_body, name="请求体(原始字符串)", attachment_type=allure.attachment_type.TEXT)
        # 用 data= 传原始字符串，不设 Content-Type（requests 默认不设）
        resp = api.post(SIGN_IN_ENDPOINT, data=raw_body.encode("utf-8"))

    with allure.step("断言响应"):
        allure.attach(resp.text[:4000], name="响应体", attachment_type=allure.attachment_type.JSON)
        assert_status_code(resp, 200)
        assert_jsonpath(resp, "$.code", -100)
        assert_contains(resp, "出错啦")