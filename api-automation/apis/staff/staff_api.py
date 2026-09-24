"""员工接口定义：岗位信息（svc-main 服务）。"""
from __future__ import annotations

from common.request_handler import RequestHandler

_SERVICE = "svc-main"
_INFO_ENDPOINT = "/api/staff/info"


def get_info(api: RequestHandler):
    """员工详情（含岗位列表）GET /svc-main/api/staff/info

    返回 staffPositionList，供 apply_biz_auth 提取岗位头。
    """
    return api.get(f"{api.config.service_url(_SERVICE)}{_INFO_ENDPOINT}")
