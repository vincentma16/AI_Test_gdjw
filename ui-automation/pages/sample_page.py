"""示例页 Page Object：演示 Page Object 写法，同时作为容器自检用例的载体。

接入真实系统后，按同样方式为你的页面建 pages/<模块>/<模块>_page.py，
本文件即可删除。
"""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Locator, Page

from pages.base_page import BasePage

_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


class SamplePage(BasePage):
    """示例页：输入关键字 -> 点击查询 -> 查看结果提示。"""

    _submit_btn_name = "查 询"  # 注意中间的全角空格

    @property
    def keyword_input(self) -> Locator:
        """关键字输入框。"""
        return self.page.get_by_placeholder("请输入关键字").first

    @property
    def submit_btn(self) -> Locator:
        """查询按钮（文本 "查 询"，注意空格）。"""
        return self.page.get_by_role("button", name=self._submit_btn_name).first

    @property
    def result_msg(self) -> Locator:
        """结果提示区域。"""
        return self.page.locator("#msg").first

    def open(self, home_url: str):
        """打开页面。fixture:// 前缀加载本地 HTML，否则访问真实地址。"""
        if home_url.startswith("fixture://"):
            fixture_path = _FIXTURES_DIR / home_url[len("fixture://"):]
            self.navigate(fixture_path.as_uri())
        else:
            self.navigate(home_url)
        return self

    def search(self, keyword: str):
        """输入关键字并点击查询。"""
        self.fill(self.keyword_input, keyword, "关键字")
        self.click(self.submit_btn, "查询按钮")
