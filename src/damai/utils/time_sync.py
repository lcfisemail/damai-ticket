"""NTP 时间同步工具"""
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import ntplib
from loguru import logger

_time_offset: float = 0.0  # 本地时间与NTP的偏差秒数


def sync_time(ntp_server: str = "ntp.aliyun.com") -> float:
    """
    同步NTP时间，返回时间偏差（秒）。
    之后调用 accurate_time() 会自动补偿此偏差。
    """
    global _time_offset
    try:
        client = ntplib.NTPClient()
        response = client.request(ntp_server, version=3, timeout=3)
        _time_offset = response.offset
        logger.info(f"NTP同步成功，时间偏差: {_time_offset:.3f}s (服务器: {ntp_server})")
        return _time_offset
    except Exception as e:
        logger.warning(f"NTP同步失败: {e}，使用本地时间")
        _time_offset = 0.0
        return 0.0


def accurate_time() -> float:
    """返回NTP校准后的当前时间（Unix时间戳，秒）"""
    return time.time() + _time_offset


def accurate_timestamp_ms() -> str:
    """返回NTP校准后的毫秒时间戳字符串"""
    return str(int(accurate_time() * 1000))


def sleep_until(target_ts: float, pre_wake_seconds: float = 0.0) -> None:
    """
    阻塞睡眠直到目标时间戳。
    pre_wake_seconds: 提前唤醒的秒数（用于在开售前几秒开始抢）
    """
    wake_at = target_ts - pre_wake_seconds
    now = accurate_time()
    if wake_at > now:
        sleep_duration = wake_at - now
        logger.info(f"等待开售，将在 {sleep_duration:.1f}s 后开始 (提前 {pre_wake_seconds}s)")
        time.sleep(sleep_duration)


def parse_sale_start_time(time_str: str) -> Optional[float]:
    """
    解析开售时间字符串为 Unix 时间戳。
    支持格式: "2025-01-01T20:00:00+08:00" 或 "2025-01-01 20:00:00"
    """
    if not time_str:
        return None
    try:
        # 尝试 ISO 8601 格式
        if "T" in time_str:
            dt = datetime.fromisoformat(time_str)
        else:
            # 假设为北京时间 (UTC+8)
            dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            dt = dt.replace(tzinfo=timezone(timedelta(hours=8)))
        return dt.timestamp()
    except ValueError as e:
        logger.error(f"解析开售时间失败: {e}")
        return None
