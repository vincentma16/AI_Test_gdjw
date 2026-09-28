"""框架自检用例：验证 Page Object + 浏览器 + 数据驱动这条链路可用。

跑的是本地 fixtures/sample.html，不联网，因此常被用来确认容器环境是否健康。
接入真实系统后可整体删除本目录。
"""
from __future__ import annotations

from pathlib import Path

import allure
import pytest
import yaml

from common.assert_util import assert_contains_text, assert_visible
from pages.sample_page import SamplePage

# 用例在 testcases/<模块>/ 下，数据在项目根 data/ 下，故向上 3 级定位项目根
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DATA_FILE = _PROJECT_ROOT / "data" / "sample.yaml"

with open(_DATA_FILE, "r", encoding="utf-8") as _f:
    _DATA = yaml.safe_load(_f)

_CASES = _DATA["cases"]


@pytest.mark.parametrize(
    "case",
    _CASES,
    ids=[c["id"] for c in _CASES],
)
def test_sample_search(page, config, case):
    """本地 fixture 自检用例（数据驱动）。"""
    if config.env != "local":
        pytest.skip("自检用例仅在 local 环境运行")

    allure.dynamic.feature(case["feature"])
    allure.dynamic.story(case["story"])
    allure.dynamic.title(f'{case["id"]} {case["name"]}')

    sample_page = SamplePage(page)

    with allure.step("打开示例页"):
        sample_page.open(config.home_url)

    with allure.step("执行查询操作"):
        sample_page.search(case["request"]["keyword"])

    with allure.step("断言查询结果"):
        expect = case["expect"]
        if "success_text" in expect:
            assert_contains_text(sample_page.result_msg, expect["success_text"], "结果提示文本")
        elif "error_text" in expect:
            assert_visible(sample_page.result_msg, "结果提示")
            assert_contains_text(sample_page.result_msg, expect["error_text"], "结果提示文本")

    sample_page.screenshot("查询结果")
