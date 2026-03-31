"""通知器抽象接口"""
from typing import Protocol, runtime_checkable


@runtime_checkable
class Notifier(Protocol):
    async def send(self, title: str, body: str, level: str = "info") -> bool:
        """发送通知，返回是否成功"""
        ...


class NotificationDispatcher:
    """通知分发器，向所有配置的通知渠道并发发送"""

    def __init__(self, notifiers: list[Notifier]):
        self._notifiers = notifiers

    async def send(self, title: str, body: str, level: str = "info") -> None:
        import asyncio
        from loguru import logger

        if not self._notifiers:
            return

        results = await asyncio.gather(
            *[n.send(title, body, level) for n in self._notifiers],
            return_exceptions=True,
        )
        for notifier, result in zip(self._notifiers, results):
            if isinstance(result, Exception):
                logger.warning(f"通知发送失败 [{type(notifier).__name__}]: {result}")
