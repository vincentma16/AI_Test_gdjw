"""示例接口定义：演示 apis 层写法（接入新项目后可删除或改造）。

每个 *_api.py 文件包含三部分：
  1. 接口路径常量（大写+下划线）
  2. 接口函数（第一参数 api: RequestHandler，keyword-only，返回 raw Response）
  3. 内部辅助函数（_ 开头）

用例只调用本层函数，不拼 URL、不组装 payload。
"""
from __future__ import annotations

from common.request_handler import RequestHandler

# 1. 接口路径常量
EXAMPLE_ENDPOINT = "/api/example/info"
_SERVICE = "example-service"   # 对应 config.yaml services 中的服务名
_PREFIX = "/api/example"


def _url(api: RequestHandler, path: str) -> str:
    """拼接业务服务完整 URL。"""
    return f"{api.config.service_url(_SERVICE)}{_PREFIX}{path}"


def get_info(api: RequestHandler):
    """查询示例信息 GET /api/example/info（走 base_url）。"""
    return api.get(EXAMPLE_ENDPOINT)


def create(api: RequestHandler, *, name: str, **extra):
    """新增示例 POST /api/example/create（走 service_url）。

    Args:
        name: 名称（必填，keyword-only）
        **extra: 其他可选字段透传
    Returns: requests.Response
    """
    payload = {"name": name}
    payload.update(extra)
    return api.post(_url(api, "/create"), json=payload)