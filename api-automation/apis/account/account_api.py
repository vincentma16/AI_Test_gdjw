"""账号接口定义：登录 / 账号信息（auth 服务，走 base_url 域名）。"""
from __future__ import annotations

from common.request_handler import RequestHandler

# 接口路径常量（用例与数据层也可引用，不重复硬编码）
SIGN_IN_ENDPOINT = "/auth/account/signInByVerifyCode"
USER_INFO_ENDPOINT = "/auth/account/userInfo"


def sign_in_by_verify_code(
    api: RequestHandler, mobile: str, verify_code: str, client_id: str
):
    """验证码登录 POST /auth/account/signInByVerifyCode

    Returns: requests.Response
    """
    return api.post(
        SIGN_IN_ENDPOINT,
        json={"mobile": mobile, "verifyCode": verify_code, "clientId": client_id},
    )


def get_user_info(api: RequestHandler):
    """获取用户信息 GET /auth/account/userInfo"""
    return api.get(USER_INFO_ENDPOINT)
