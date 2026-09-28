"""断言工具：UI 元素可见性、文本、URL、标题（自动等待）。"""
from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from common.logger import logger


def assert_visible(locator: Locator, description: str = "", timeout: int = 10000):
    """断言元素可见（自动等待）。"""
    expect(locator).to_be_visible(timeout=timeout)
    logger.debug("断言可见: %s", description or "元素")


def assert_text(locator: Locator, expected: str, description: str = "", timeout: int = 10000):
    """断言元素文本完全匹配。"""
    expect(locator).to_have_text(expected, timeout=timeout)
    logger.debug("断言文本: %s 期望=%s", description or "元素", expected)


def assert_contains_text(locator: Locator, text: str, description: str = "", timeout: int = 10000):
    """断言元素文本包含指定内容。"""
    expect(locator).to_contain_text(text, timeout=timeout)
    logger.debug("断言包含文本: %s 期望包含=%s", description or "元素", text)


def assert_url_contains(page: Page, fragment: str):
    logger.debug("断言URL包含: %s 实际=%s", fragment, page.url)
    assert fragment in page.url, f"URL 不包含 {fragment!r}, 实际: {page.url}"


def assert_title_contains(page: Page, fragment: str):
    actual = page.title()
    logger.debug("断言标题包含: %s 实际=%s", fragment, actual)
    assert fragment in actual, f"标题不包含 {fragment!r}, 实际: {actual}"
