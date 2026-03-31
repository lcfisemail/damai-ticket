"""企业微信机器人 webhook 通知"""
import httpx
from loguru import logger


class WechatNotifier:
    """企业微信群机器人通知"""

    def __init__(self, webhook_url: str):
        self._webhook_url = webhook_url

    async def send(self, title: str, body: str, level: str = "info") -> bool:
        emoji = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}.get(level, "ℹ️")
        content = f"## {emoji} {title}\n\n{body}"

        payload = {
            "msgtype": "markdown",
            "markdown": {"content": content},
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(self._webhook_url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                if data.get("errcode") == 0:
                    return True
                logger.warning(f"企业微信通知失败: {data}")
                return False
        except Exception as e:
            logger.error(f"企业微信通知异常: {e}")
            return False
