"""响应提取：从响应中按 jsonpath/正则提取值，供链路用例复用。"""
from __future__ import annotations

import re
from typing import Any

from jsonpath_ng import parse as jsonpath_parse

from common.logger import logger


def extract_by_jsonpath(resp, expr: str) -> Any:
    data = resp.json()
    matches = [m.value for m in jsonpath_parse(expr).find(data)]
    if not matches:
        raise ValueError(f"jsonpath 未匹配: {expr}; 响应: {resp.text[:500]}")
    logger.debug("提取 jsonpath %s = %s", expr, matches[0])
    return matches[0]


def extract_by_regex(resp, pattern: str, group: int = 1) -> str:
    m = re.search(pattern, resp.text)
    if not m:
        raise ValueError(f"正则未匹配: {pattern}; 响应: {resp.text[:500]}")
    value = m.group(group)
    logger.debug("提取 regex %s = %s", pattern, value)
    return value


class Context:
    """链路用例间的变量上下文，支持 ${var} 占位符替换。"""

    def __init__(self):
        self._store: dict[str, Any] = {}

    def set(self, key: str, value: Any):
        self._store[key] = value

    def get(self, key: str) -> Any:
        return self._store.get(key)

    def render(self, obj: Any) -> Any:
        """递归替换 ${var} 占位符。"""
        if isinstance(obj, str):
            for k, v in self._store.items():
                obj = obj.replace("${" + k + "}", str(v))
            return obj
        if isinstance(obj, dict):
            return {k: self.render(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self.render(v) for v in obj]
        return obj
