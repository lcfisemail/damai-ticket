"""钉钉机器人 webhook 通知"""
import base64
import hashlib
import hmac
import time
import urllib.parse

import httpx
from loguru import logger


class DingtalkNotifier:
    """钉钉自定义机器人通知（支持加签）"""

    def __init__(self, webhook_url: str, secret: str = ""):
        self._webhook_url = webhook_url
        self._secret = secret

    def _sign(self) -> tuple[str, str]:
        """生成时间戳和签名"""
        timestamp = str(round(time.time() * 1000))
        if not self._secret:
            return timestamp, ""
        string_to_sign = f"{timestamp}\n{self._secret}"
        hmac_code = hmac.new(
            self._secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return timestamp, sign

    async def send(self, title: str, body: str, level: str = "info") -> bool:
        timestamp, sign = self._sign()
        url = self._webhook_url
        if sign:
            url = f"{url}&timestamp={timestamp}&sign={sign}"

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": f"## {title}\n\n{body}",
            },
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                if data.get("errcode") == 0:
                    return True
                logger.warning(f"钉钉通知失败: {data}")
                return False
        except Exception as e:
            logger.error(f"钉钉通知异常: {e}")
            return False
