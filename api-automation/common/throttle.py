"""请求节流：按 key（如手机号）强制最小间隔，避免触发接口频控。

实测登录接口对同一手机号有 5 秒频控，且被限请求会重置倒计时。
因此采用"主动节流"：同一 key 的请求间隔强制 >= min_gap，从源头避免触发。
auth 登录与测试用例共享同一 login_throttle 实例，避免互相干扰。
"""
from __future__ import annotations

import threading
import time

from common.logger import logger


class Throttle:
    """按 key 强制最小请求间隔。线程安全。"""

    def __init__(self, min_gap: float = 6.0):
        self._min_gap = min_gap
        self._last: dict[str, float] = {}
        self._lock = threading.Lock()

    def wait(self, key) -> None:
        """若距上次同 key 请求不足 min_gap，则阻塞等待。"""
        if not key:
            return
        key = str(key)  # 归一化：数字类型与字符串同值视为同一 key
        with self._lock:
            now = time.monotonic()
            last = self._last.get(key)
            if last is not None:
                gap = self._min_gap - (now - last)
                if gap > 0:
                    logger.info("节流: key=%s 等待 %.1fs", key, gap)
                    time.sleep(gap)
            self._last[key] = time.monotonic()


# 全局共享实例：登录接口频控窗口 5s，留 1s 余量
login_throttle = Throttle(min_gap=6.0)
