"""登录鉴权：获取 token 并按配置注入请求头与查询参数。"""
from __future__ import annotations

from urllib.parse import quote

from common.extractor import extract_by_jsonpath
from common.logger import logger
from common.request_handler import RequestHandler
from common.throttle import login_throttle


def login(api: RequestHandler, auth_cfg: dict) -> str:
    """执行登录并返回 access_token。"""
    endpoint = auth_cfg["login_endpoint"]
    credentials = auth_cfg.get("credentials", {})
    login_throttle.wait(credentials.get("mobile"))
    resp = api.post(endpoint, json=credentials)
    token = extract_by_jsonpath(resp, auth_cfg["token_jsonpath"])
    logger.info("登录成功，已获取 access_token")
    return token


def apply_auth(api: RequestHandler, auth_cfg: dict, token: str) -> None:
    """按配置将 token 注入 session 默认请求头与查询参数（auth 接口鉴权）。"""
    header_cfg = auth_cfg.get("header")
    if header_cfg and header_cfg.get("name"):
        prefix = header_cfg.get("prefix", "")
        api.session.headers[header_cfg["name"]] = f"{prefix}{token}"
        logger.info("已注入鉴权请求头: %s", header_cfg["name"])
    query_cfg = auth_cfg.get("query_param")
    if query_cfg and query_cfg.get("name"):
        api.default_params[query_cfg["name"]] = token
        logger.info("已注入鉴权查询参数: %s", query_cfg["name"])


def apply_biz_auth(api: RequestHandler, cfg, token: str) -> None:
    """业务接口鉴权（svc-main/svc-deal/svc-bill）：
    1. 注入业务鉴权头（Authorization/token/access-token/Business-Line）
    2. 调用 staff/info 拉取岗位，注入岗位头（postcode/orgCode 等，权限校验需要）
    """
    auth_cfg = cfg.auth
    # 1. 业务鉴权头
    biz_headers = auth_cfg.get("biz_headers", [])
    for h in biz_headers:
        name = h["name"]
        if "value" in h:
            api.session.headers[name] = h["value"]
        else:
            prefix = h.get("prefix", "")
            api.session.headers[name] = f"{prefix}{token}"
    logger.info("已注入业务鉴权头: %s", [h["name"] for h in biz_headers])

    # 2. 岗位信息
    staff = auth_cfg.get("staff_info")
    if not staff:
        return
    base = cfg.service_url(staff["service"])
    method = staff.get("method", "GET").upper()
    resp = api.request(method, base + staff["endpoint"])
    positions = extract_by_jsonpath(resp, staff["positions_jsonpath"])
    if not positions:
        raise RuntimeError(f"未获取到岗位信息: {resp.text[:500]}")
    pos = positions[0]
    orgs = pos.get(staff.get("org_key", "organizationDtoList")) or []
    org = orgs[0] if orgs else {}
    role_headers = staff.get("role_headers", {})
    for header_name, spec in role_headers.items():
        field = spec["field"] if isinstance(spec, dict) else spec
        val = pos.get(field) if pos.get(field) else org.get(field, "")
        if isinstance(spec, dict) and spec.get("encode"):
            val = quote(str(val))
        api.session.headers[header_name] = str(val)
    logger.info("已注入岗位头: 岗位=%s 组织=%s", pos.get("postName"), org.get("orgName"))
