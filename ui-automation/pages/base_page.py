"""页面基类：封装 Playwright 公共操作与 Allure 步骤。"""
from __future__ import annotations

import allure
from playwright.sync_api import Locator, Page

from common.logger import logger


class BasePage:
    """所有 Page Object 的基类。"""

    def __init__(self, page: Page):
        self.page = page

    def navigate(self, url: str):
        logger.info("导航: %s", url)
        self.page.goto(url)

    def click(self, locator: Locator, name: str = ""):
        logger.info("点击: %s", name or "元素")
        with allure.step(f"点击 {name}"):
            locator.click()

    def fill(self, locator: Locator, text: str, name: str = ""):
        logger.info("输入: %s = %s", name or "元素", text)
        with allure.step(f"输入 {name}"):
            locator.fill(text)

    def get_text(self, locator: Locator) -> str:
        return locator.inner_text()

    def screenshot(self, name: str = "截图"):
        png = self.page.screenshot()
        allure.attach(png, name=name, attachment_type=allure.attachment_type.PNG)

    def wait_for_selector(self, selector: str, timeout: int | None = None) -> Locator:
        return self.page.wait_for_selector(selector, timeout=timeout)
