"""登录鉴权：获取 token 并按配置注入请求头与查询参数。

这是**参考实现**，按 config/config.yaml 的 auth 段执行，不硬编码任何接口细节。
被测系统的鉴权方式若是别的形式（cookie、签名、双 token 等），照这个骨架改写即可。
"""
from __future__ import annotations

from common.extractor import extract_by_jsonpath
from common.logger import logger
from common.request_handler import RequestHandler
from common.throttle import request_throttle


def login(api: RequestHandler, auth_cfg: dict) -> str:
    """执行登录并返回 token。"""
    endpoint = auth_cfg["login_endpoint"]
    credentials = auth_cfg.get("credentials", {})
    # 同一账号的连续登录容易撞频控，先节流
    throttle_key = next(iter(credentials.values()), None) if credentials else None
    request_throttle.wait(throttle_key)
    resp = api.post(endpoint, json=credentials)
    token = extract_by_jsonpath(resp, auth_cfg["token_jsonpath"])
    logger.info("登录成功，已获取 token")
    return token


def apply_auth(api: RequestHandler, auth_cfg: dict, token: str) -> None:
    """按配置将 token 注入 session 默认请求头与查询参数。"""
    header_cfg = auth_cfg.get("header")
    if header_cfg and header_cfg.get("name"):
        prefix = header_cfg.get("prefix", "")
        api.session.headers[header_cfg["name"]] = f"{prefix}{token}"
        logger.info("已注入鉴权请求头: %s", header_cfg["name"])
    query_cfg = auth_cfg.get("query_param")
    if query_cfg and query_cfg.get("name"):
        api.default_params[query_cfg["name"]] = token
        logger.info("已注入鉴权查询参数: %s", query_cfg["name"])
