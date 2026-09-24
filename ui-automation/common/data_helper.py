"""测试数据生成工具。

随机手机号、时间戳名称等生成逻辑集中在此，供用例调用，
避免在各用例中重复编写生成代码（减少代码量与出错概率）。
"""
from __future__ import annotations

import random
import time


def random_mobile(prefix: str = "138") -> str:
    """生成随机 11 位手机号，避免重复客户导致用例失败。"""
    return f"{prefix}{random.randint(10000000, 99999999):08d}"


def timestamped_name(base: str, fmt: str = "%m%d%H%M%S") -> str:
    """给名称加时间戳后缀，避免重复。"""
    return f"{base}_{time.strftime(fmt)}"
