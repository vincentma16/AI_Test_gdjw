"""示例用例：演示用例层写法（接入新系统后可删除或改造为首个业务模块）。

用例铁律：只调用 apis 函数，不拼 URL、不存放参数。
"""
from __future__ import annotations

import allure
import pytest

from apis.example import example_api
from common.assert_util import assert_status_code


@pytest.mark.regression
@allure.feature("示例模块")
@allure.story("示例查询")
def test_get_example_info(api):
    """调用示例查询接口并断言（api 为 session 级请求句柄，见 conftest.py）。"""
    if "example.com" in api.config.base_url:
        pytest.skip("尚未接入真实被测系统（base_url 仍为占位值），示例不执行")

    allure.dynamic.title("EXAMPLE-API-001 示例查询成功")
    allure.dynamic.description("排查点：验证示例查询接口正常返回")

    resp = example_api.get_info(api)
    allure.attach(resp.text[:4000], name="响应体", attachment_type=allure.attachment_type.JSON)
    assert_status_code(resp, 200)
    # TODO: 按实际响应结构断言，示例：
    # assert_jsonpath(resp, "$.code", 0)
