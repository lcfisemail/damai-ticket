"""
大麦网 mTOP 协议客户端

mTOP (Mobile Technology Open Platform) 是阿里巴巴的移动端开放平台协议。
所有大麦网 API 通过此协议调用。

签名算法:
    sign = MD5(token + "&" + timestamp + "&" + appKey + "&" + data_json)

其中 token 从 cookie _m_h5_tk 中提取（下划线前的部分）。
"""
from __future__ import annotations

import asyncio
import json
import random
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
from loguru import logger

from damai.constants import (
    DEFAULT_HEADERS,
    MTOP_BASE_URL,
    MTOP_ERR_CAPTCHA,
    MTOP_ERR_TOKEN_EXPIRED,
    MTOP_ERR_TRAFFIC_LIMIT,
    MTOP_H5_APP_KEY,
    MTOP_JSV,
    MTOP_SUCCESS_CODE,
)
from damai.exceptions import (
    CaptchaRequiredError,
    MtopError,
    TokenExpiredError,
    TrafficLimitError,
)
from damai.utils.crypto import extract_token_from_h5tk, md5_sign
from damai.utils.time_sync import accurate_timestamp_ms


class MtopResponse:
    """mTOP 响应封装"""

    def __init__(self, raw: dict):
        self.raw = raw
        self.ret: list[str] = raw.get("ret", [])
        self.data: dict = raw.get("data", {})
        self.api: str = raw.get("api", "")

    @property
    def is_success(self) -> bool:
        return any(r.startswith(MTOP_SUCCESS_CODE) for r in self.ret)

    @property
    def error_codes(self) -> list[str]:
        return [r for r in self.ret if not r.startswith(MTOP_SUCCESS_CODE)]

    def has_error(self, code: str) -> bool:
        return any(code in r for r in self.ret)

    def __repr__(self) -> str:
        return f"MtopResponse(ret={self.ret}, data_keys={list(self.data.keys())})"


class MtopClient:
    """
    大麦网 mTOP 协议客户端

    使用示例:
        async with httpx.AsyncClient() as session:
            client = MtopClient(session)
            resp = await client.execute("mtop.alibaba.damai.detail.getdetail", "1.0", {...})
    """

    def __init__(
        self,
        session: httpx.AsyncClient,
        app_key: str = MTOP_H5_APP_KEY,
        jsv: str = MTOP_JSV,
    ):
        self._session = session
        self._app_key = app_key
        self._jsv = jsv
        self._token: Optional[str] = None  # 从 _m_h5_tk cookie 提取

    def _get_token(self) -> str:
        """从 httpx cookie jar 中提取 mTOP token"""
        h5tk = ""
        try:
            h5tk = self._session.cookies.get("_m_h5_tk") or ""
        except Exception:
            h5tk = ""

        if not h5tk:
            preferred_domains = ("damai.cn", "m.damai.cn")
            fallback_value = ""
            for cookie in self._session.cookies.jar:
                if cookie.name != "_m_h5_tk":
                    continue
                cookie_domain = (cookie.domain or "").lstrip(".")
                if cookie_domain.endswith(preferred_domains):
                    h5tk = cookie.value
                    break
                if not fallback_value:
                    fallback_value = cookie.value
            if not h5tk:
                h5tk = fallback_value
        if h5tk:
            return extract_token_from_h5tk(h5tk)
        return ""

    def _build_url(self, api: str, version: str, timestamp: str, sign: str) -> str:
        """构建 mTOP 请求 URL"""
        params = {
            "jsv": self._jsv,
            "appKey": self._app_key,
            "t": timestamp,
            "sign": sign,
            "api": api,
            "v": version,
            "type": "originaljson",
            "dataType": "json",
            "timeout": "15000",
            "AntiCreep": "true",
        }
        base = f"{MTOP_BASE_URL}{api}/{version}/"
        return f"{base}?{urlencode(params)}"

    async def execute(
        self,
        api: str,
        version: str,
        data: dict[str, Any],
        method: str = "POST",
        retry_on_token_expired: bool = True,
    ) -> MtopResponse:
        """
        执行 mTOP API 调用

        Args:
            api: API 名称，如 "mtop.alibaba.damai.detail.getdetail"
            version: API 版本，如 "1.0"
            data: 请求数据字典
            method: HTTP 方法
            retry_on_token_expired: token 过期时是否自动刷新并重试
        """
        timestamp = accurate_timestamp_ms()
        token = self._get_token()
        data_json = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        sign = md5_sign(token, timestamp, self._app_key, data_json)

        url = self._build_url(api, version, timestamp, sign)

        headers = dict(DEFAULT_HEADERS)
        headers["Referer"] = "https://m.damai.cn/damai/detail/item.html"

        try:
            if method.upper() == "POST":
                resp = await self._session.post(
                    url,
                    data={"data": data_json},
                    headers=headers,
                    timeout=15.0,
                )
            else:
                resp = await self._session.get(url, headers=headers, timeout=15.0)

            resp.raise_for_status()
            result = resp.json()

        except httpx.HTTPStatusError as e:
            raise MtopError(f"HTTP错误: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise MtopError(f"请求失败: {e}") from e
        except json.JSONDecodeError as e:
            raise MtopError(f"响应解析失败: {e}") from e

        mtop_resp = MtopResponse(result)

        # 处理 token 过期
        if mtop_resp.has_error(MTOP_ERR_TOKEN_EXPIRED):
            if retry_on_token_expired:
                logger.debug("Token 已过期，正在刷新...")
                await self._refresh_token()
                return await self.execute(api, version, data, method, retry_on_token_expired=False)
            raise TokenExpiredError("Token已过期且刷新失败")

        # 处理限流
        if mtop_resp.has_error(MTOP_ERR_TRAFFIC_LIMIT):
            raise TrafficLimitError(
                f"请求被限流: {mtop_resp.ret}",
                ret_codes=mtop_resp.ret,
            )

        # 处理验证码
        if mtop_resp.has_error(MTOP_ERR_CAPTCHA):
            raise CaptchaRequiredError(
                f"需要验证码: {mtop_resp.ret}",
                captcha_data=mtop_resp.data,
            )

        if not mtop_resp.is_success:
            logger.warning(f"mTOP 调用失败 [{api}]: {mtop_resp.ret}")

        return mtop_resp

    async def execute_with_retry(
        self,
        api: str,
        version: str,
        data: dict[str, Any],
        max_retries: int = 3,
        backoff_base: float = 0.1,
    ) -> MtopResponse:
        """带指数退避重试的 execute"""
        last_err: Optional[Exception] = None
        for attempt in range(max_retries):
            try:
                return await self.execute(api, version, data)
            except TrafficLimitError as e:
                last_err = e
                wait = backoff_base * (2 ** attempt) + random.uniform(0, 0.05)
                logger.warning(f"限流，{wait:.2f}s 后重试 ({attempt + 1}/{max_retries})")
                await asyncio.sleep(wait)
            except CaptchaRequiredError:
                raise  # 验证码需要用户处理，不自动重试
        raise last_err or MtopError("重试次数耗尽")

    async def _refresh_token(self) -> None:
        """通过轻量 API 刷新 _m_h5_tk token"""
        try:
            await self._session.get(
                "https://m.damai.cn/",
                headers={"User-Agent": DEFAULT_HEADERS["User-Agent"]},
                timeout=10.0,
                follow_redirects=True,
            )
            logger.debug("Token 刷新成功")
        except Exception as e:
            logger.warning(f"Token 刷新失败: {e}")
