"""鉴权 fixture 演示：登录获取 token 并自动注入后续请求。

对比同一接口在「无鉴权」与「auth_api 自动注入 token」下的结果。
接口 /auth/account/userInfo 的鉴权方式为查询参数 accessToken
（来源：/auth/v2/api-docs）。

接口路径与调用统一走 apis.account.account_api，用例不硬编码 URL。
"""
from __future__ import annotations

import allure
import pytest

from apis.account import account_api
from common.assert_util import assert_jsonpath, assert_status_code


@pytest.mark.auth
def test_user_info_without_auth(api):
    """无 token 调用应失败，证明接口需要鉴权。"""
    allure.dynamic.feature("鉴权")
    allure.dynamic.story("无鉴权调用-失败")
    resp = account_api.get_user_info(api)
    assert_status_code(resp, 200)
    # 无 accessToken 时业务码非 0
    assert resp.json()["code"] != 0


@pytest.mark.auth
def test_user_info_with_auth(auth_api):
    """auth_api 自动注入 accessToken，调用应成功。"""
    allure.dynamic.feature("鉴权")
    allure.dynamic.story("自动注入token-成功")
    resp = account_api.get_user_info(auth_api)
    allure.attach(
        resp.text[:4000],
        name="响应体",
        attachment_type=allure.attachment_type.JSON,
    )
    assert_status_code(resp, 200)
    assert_jsonpath(resp, "$.code", 0)
    assert_jsonpath(resp, "$.message", "success")