"""代理池管理"""
import asyncio
import random
from typing import Optional

import httpx
from loguru import logger


class ProxyManager:
    """
    代理池管理器

    支持 HTTP/HTTPS/SOCKS5 代理。
    可以账号绑定（pin_per_account=True），也可以每请求随机轮换。
    """

    def __init__(self, proxies: list[str], pin_per_account: bool = True):
        self._all_proxies = list(proxies)
        self._healthy_proxies: list[str] = []
        self._pin_per_account = pin_per_account
        self._account_proxy_map: dict[str, str] = {}
        self._index = 0

    @property
    def is_empty(self) -> bool:
        return len(self._healthy_proxies) == 0

    async def health_check(self, timeout: float = 5.0) -> None:
        """并发健康检查所有代理"""
        if not self._all_proxies:
            return

        async def check_one(proxy: str) -> Optional[str]:
            try:
                async with httpx.AsyncClient(proxy=proxy, timeout=timeout) as client:
                    resp = await client.get("https://m.damai.cn/", follow_redirects=True)
                    if resp.status_code < 500:
                        return proxy
            except Exception:
                pass
            return None

        logger.info(f"检查 {len(self._all_proxies)} 个代理...")
        results = await asyncio.gather(*[check_one(p) for p in self._all_proxies])
        self._healthy_proxies = [p for p in results if p is not None]
        logger.info(f"可用代理: {len(self._healthy_proxies)}/{len(self._all_proxies)}")

    def get_next(self) -> Optional[str]:
        """获取下一个可用代理（轮询）"""
        if not self._healthy_proxies:
            return None
        proxy = self._healthy_proxies[self._index % len(self._healthy_proxies)]
        self._index += 1
        return proxy

    def get_for_account(self, account_id: str) -> Optional[str]:
        """为账号获取绑定代理（如果启用账号绑定）"""
        if not self._pin_per_account:
            return self.get_next()

        if account_id not in self._account_proxy_map:
            proxy = self.get_next()
            if proxy:
                self._account_proxy_map[account_id] = proxy
            return proxy

        # 检查绑定的代理是否还健康
        pinned = self._account_proxy_map[account_id]
        if pinned in self._healthy_proxies:
            return pinned

        # 重新分配
        new_proxy = self.get_next()
        if new_proxy:
            self._account_proxy_map[account_id] = new_proxy
        return new_proxy

    def mark_failed(self, proxy: str) -> None:
        """标记代理为不可用"""
        if proxy in self._healthy_proxies:
            self._healthy_proxies.remove(proxy)
            logger.warning(f"代理已移除: {proxy}，剩余 {len(self._healthy_proxies)} 个")
