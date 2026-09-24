"""断言工具：状态码、jsonpath、jsonschema、字段包含。"""
from __future__ import annotations

import json
from typing import Any

from jsonpath_ng import parse as jsonpath_parse

from common.logger import logger


def assert_status_code(resp, expected: int):
    actual = resp.status_code
    logger.debug("断言状态码: 期望=%s 实际=%s", expected, actual)
    assert actual == expected, (
        f"状态码不匹配: 期望 {expected}, 实际 {actual}; 响应: {resp.text[:500]}"
    )


def assert_jsonpath(resp, expr: str, expected: Any):
    """断言响应中 jsonpath 取值等于 expected。"""
    data = _as_json(resp)
    matches = [m.value for m in jsonpath_parse(expr).find(data)]
    assert matches, f"jsonpath 未匹配到任何值: {expr}; 响应: {resp.text[:500]}"
    actual = matches[0]
    logger.debug("断言 jsonpath: %s 期望=%s 实际=%s", expr, expected, actual)
    assert actual == expected, (
        f"jsonpath {expr} 不匹配: 期望 {expected!r}, 实际 {actual!r}"
    )


def assert_jsonpath_exists(resp, expr: str):
    """断言响应中 jsonpath 路径存在且非空。"""
    data = _as_json(resp)
    matches = [m.value for m in jsonpath_parse(expr).find(data)]
    assert matches and matches[0] not in (None, "", []), (
        f"jsonpath 不存在或为空: {expr}; 响应: {resp.text[:500]}"
    )


def assert_contains(resp, text: str):
    logger.debug("断言包含: %s", text)
    assert text in resp.text, f"响应未包含 {text!r}; 响应: {resp.text[:500]}"


def assert_json_schema(resp, schema: dict):
    """校验响应是否符合 jsonschema。"""
    from jsonschema import validate

    data = _as_json(resp)
    validate(instance=data, schema=schema)


def _as_json(resp):
    try:
        return resp.json()
    except json.JSONDecodeError as e:
        raise AssertionError(f"响应非 JSON: {resp.text[:500]}") from e
