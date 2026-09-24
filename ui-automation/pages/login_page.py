"""登录页 Page Object：手机号 + 验证码授权登录（sso 登录页）。"""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Locator, Page

from pages.base_page import BasePage

_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


class LoginPage(BasePage):
    """登录页，验证码授权登录流程。

    真实流程：访问 web 入口 -> 重定向到 sso 登录页 ->
    选择「验证码授权」-> 输入手机号 + 验证码 -> 点击登录 -> 跳回 web 工作台。
    """

    _verify_code_tab = "验证码授权"
    _login_btn_name = "登 录"  # 注意中间的全角空格

    @property
    def verify_code_tab(self) -> Locator:
        return self.page.get_by_text(self._verify_code_tab).first

    @property
    def phone_input(self) -> Locator:
        """手机号输入框（sso 多登录方式共存于 DOM，须过滤可见）。"""
        return self.page.get_by_placeholder("请输入手机号").filter(visible=True).first

    @property
    def code_input(self) -> Locator:
        """验证码输入框（过滤可见）。"""
        return self.page.get_by_placeholder("验证码").filter(visible=True).first

    @property
    def login_btn(self) -> Locator:
        """登录按钮（文本 "登 录"，注意空格）。"""
        return self.page.get_by_role("button", name=self._login_btn_name).filter(
            visible=True
        ).first

    @property
    def success_msg(self) -> Locator:
        """本地 fixture 的成功提示。"""
        return self.page.locator("text=登录成功").first

    @property
    def workbench_menu(self) -> Locator:
        """工作台侧边菜单项（登录成功后 SPA 加载完成的标志）。"""
        return self.page.get_by_text("工作台").first

    def open(self, login_url: str):
        """打开登录页。fixture:// 前缀加载本地 HTML，否则访问真实 web 入口。"""
        if login_url.startswith("fixture://"):
            fixture_path = _FIXTURES_DIR / login_url[len("fixture://"):]
            self.navigate(fixture_path.as_uri())
        else:
            self.navigate(login_url)
            # 等待重定向到 sso 登录页并加载完成（等「验证码授权」标签出现，
            # 替代固定 sleep，避免网络慢时偶发失败）
            self.verify_code_tab.wait_for(state="visible", timeout=15000)
        return self

    def select_verify_code_login(self):
        """选择「验证码授权」登录方式（local fixture 无此标签则跳过）。"""
        try:
            if self.verify_code_tab.is_visible():
                self.click(self.verify_code_tab, "验证码授权")
                self.page.wait_for_timeout(800)
        except Exception:
            pass

    def login(self, phone: str, code: str):
        """执行验证码登录完整流程。"""
        self.select_verify_code_login()
        self.fill(self.phone_input, phone, "手机号")
        self.fill(self.code_input, code, "验证码")
        self.click(self.login_btn, "登录按钮")

    def wait_for_login_success(self, timeout: int = 30000) -> bool:
        """等待登录成功：URL 离开登录页，且工作台菜单加载完成。"""
        try:
            # 1. 先等 URL 离开登录页（重定向回 web）
            self.page.wait_for_url(
                lambda url: "login" not in url and "sso" not in url,
                timeout=timeout,
            )
            # 2. 再等 SPA 路由完成、侧边菜单渲染（标志工作台已加载）
            self.workbench_menu.wait_for(state="visible", timeout=timeout)
            return True
        except Exception:
            return False
