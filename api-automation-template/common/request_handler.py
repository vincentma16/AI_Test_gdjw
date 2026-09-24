"""请求封装：基于 requests.Session，统一 base_url、超时、重试与日志。"""
from __future__ import annotations

import time
import requests
from requests.adapters import HTTPAdapter

from common.config import Config
from common.logger import logger


class RequestHandler:
    """封装 requests.Session，统一注入 base_url、超时与重试。"""

    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self.default_params: dict = {}
        if config.retry > 0:
            adapter = HTTPAdapter(max_retries=config.retry)
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)

    def _url(self, endpoint: str) -> str:
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint
        return self.config.base_url + endpoint

    def request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        url = self._url(endpoint)
        kwargs.setdefault("timeout", self.config.timeout)
        # 合并默认查询参数（如 accessToken），调用方 params 优先覆盖
        params = dict(self.default_params)
        params.update(kwargs.get("params") or {})
        if params:
            kwargs["params"] = params
        logger.info("%s %s", method.upper(), url)
        if "json" in kwargs:
            logger.debug("请求体: %s", kwargs["json"])
        if params:
            logger.debug("查询参数: %s", params)
        start = time.time()
        resp = self.session.request(method, url, **kwargs)
        elapsed = round((time.time() - start) * 1000, 1)
        logger.info("响应: %s 耗时 %sms", resp.status_code, elapsed)
        logger.debug("响应体: %s", resp.text[:2000])
        return resp

    def get(self, endpoint: str, **kwargs):
        return self.request("GET", endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs):
        return self.request("POST", endpoint, **kwargs)

    def put(self, endpoint: str, **kwargs):
        return self.request("PUT", endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs):
        return self.request("DELETE", endpoint, **kwargs)

    def close(self):
        self.session.close()
