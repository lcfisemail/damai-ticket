"""
验证码处理

大麦网主要使用阿里滑动验证码（nc_token）。
默认策略是手动中继：在 GUI 中弹出验证，用户完成后将结果传回。
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class CaptchaChallenge:
    """验证码挑战数据"""
    captcha_type: str = "slider"       # 验证码类型
    image_url: str = ""                # 图片 URL（如有）
    raw_data: dict = field(default_factory=dict)  # 原始验证码数据


@dataclass
class CaptchaSolution:
    """验证码解答"""
    nc_token: str = ""                 # 滑块验证 token
    session_id: str = ""              # 会话 ID
    sig: str = ""                     # 签名
    raw_solution: dict = field(default_factory=dict)


class ManualCaptchaHandler:
    """
    手动验证码中继处理器。

    当验证码触发时，调用 on_captcha_required 回调（通常是 Qt Signal），
    然后挂起等待 GUI 用户完成验证后调用 submit_solution()。
    """

    def __init__(self, on_captcha_required: Optional[Callable[[CaptchaChallenge], None]] = None):
        self._on_captcha_required = on_captcha_required
        self._pending: Optional[asyncio.Future] = None

    async def solve(self, challenge: CaptchaChallenge) -> CaptchaSolution:
        """等待用户手动完成验证码"""
        loop = asyncio.get_running_loop()
        self._pending = loop.create_future()

        if self._on_captcha_required:
            self._on_captcha_required(challenge)

        # 等待 GUI 提交解答（最长等待 5 分钟）
        try:
            solution = await asyncio.wait_for(self._pending, timeout=300.0)
            return solution
        except asyncio.TimeoutError:
            raise TimeoutError("验证码等待超时（5分钟）")
        finally:
            self._pending = None

    def submit_solution(self, solution: CaptchaSolution) -> None:
        """由 GUI 调用，提交验证码解答"""
        if self._pending and not self._pending.done():
            self._pending.set_result(solution)

    def cancel(self) -> None:
        """取消当前等待"""
        if self._pending and not self._pending.done():
            self._pending.cancel()
