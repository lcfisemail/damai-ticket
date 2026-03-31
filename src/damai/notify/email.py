"""SMTP 邮件通知"""
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib
from loguru import logger


class EmailNotifier:
    """异步 SMTP 邮件通知"""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        to_addresses: list[str],
    ):
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._username = username
        self._password = password
        self._to_addresses = to_addresses

    async def send(self, title: str, body: str, level: str = "info") -> bool:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[大麦抢票] {title}"
        msg["From"] = self._username
        msg["To"] = ", ".join(self._to_addresses)
        msg.attach(MIMEText(body, "plain", "utf-8"))

        try:
            await aiosmtplib.send(
                msg,
                hostname=self._smtp_host,
                port=self._smtp_port,
                username=self._username,
                password=self._password,
                use_tls=True,
            )
            return True
        except Exception as e:
            logger.error(f"邮件通知失败: {e}")
            return False
