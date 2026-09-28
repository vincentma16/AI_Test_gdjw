"""浏览器封装：基于 Playwright，统一浏览器启动、上下文与超时配置。"""
from __future__ import annotations

from playwright.sync_api import Browser, BrowserContext, sync_playwright

from common.config import Config
from common.logger import logger


class BrowserFactory:
    """封装 Playwright，统一管理浏览器生命周期（session 级复用）。"""

    def __init__(self, config: Config):
        self.config = config
        self._pw = sync_playwright().start()
        self._browser: Browser | None = None

    @property
    def browser(self) -> Browser:
        if self._browser is None:
            launch_type = getattr(self._pw, self.config.browser)
            logger.info(
                "启动浏览器: %s channel=%s headless=%s slow_mo=%s",
                self.config.browser,
                self.config.channel or "(内置)",
                self.config.headless,
                self.config.slow_mo,
            )
            kwargs: dict = {
                "headless": self.config.headless,
                "slow_mo": self.config.slow_mo,
            }
            if self.config.channel:
                kwargs["channel"] = self.config.channel
            self._browser = launch_type.launch(**kwargs)
        return self._browser

    def new_context(self, storage_state: str | None = None) -> BrowserContext:
        kwargs: dict = {"viewport": {"width": 1920, "height": 1080}}
        if storage_state:
            kwargs["storage_state"] = storage_state
        ctx = self.browser.new_context(**kwargs)
        ctx.set_default_timeout(self.config.timeout)
        return ctx

    def close(self):
        if self._browser:
            self._browser.close()
        self._pw.stop()
