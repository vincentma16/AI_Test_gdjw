"""示例用例：演示用例层写法（接入新项目后可删除或改造）。

用例铁律：只调用 apis 函数，不拼 URL、不存放参数。
"""
from __future__ import annotations

import allure
import pytest

from apis.example import example_api
from common.assert_util import assert_jsonpath, assert_status_code


@pytest.mark.regression
@allure.feature("示例模块")
@allure.story("示例查询")
def test_get_example_info(auth_api):
    """调用示例查询接口并断言（auth_api 已自动注入登录 token）。"""
    allure.dynamic.title("EXAMPLE-API-001 示例查询成功")
    allure.dynamic.description("排查点：验证示例查询接口正常返回")

    resp = example_api.get_info(auth_api)
    allure.attach(resp.text[:4000], name="响应体", attachment_type=allure.attachment_type.JSON)
    assert_status_code(resp, 200)
    # TODO: 按实际响应结构断言，示例：
    # assert_jsonpath(resp, "$.code", 0)