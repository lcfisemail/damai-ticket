"""加密和签名工具"""
import hashlib
import hmac
import json
import time


def md5_sign(token: str, timestamp: str, app_key: str, data: dict | str) -> str:
    """
    大麦 mTOP H5 签名算法
    sign = MD5(token + "&" + timestamp + "&" + appKey + "&" + data_json)
    """
    if isinstance(data, dict):
        data_str = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    else:
        data_str = data

    raw = f"{token}&{timestamp}&{app_key}&{data_str}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def hmac_sha256_sign(secret: str, content: str) -> bytes:
    """HMAC-SHA256 签名，用于钉钉机器人"""
    return hmac.new(
        secret.encode("utf-8"),
        content.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()


def current_timestamp_ms() -> str:
    """返回当前毫秒级时间戳字符串"""
    return str(int(time.time() * 1000))


def extract_token_from_h5tk(h5tk: str) -> str:
    """从 _m_h5_tk cookie 值中提取 token（下划线前部分）"""
    return h5tk.split("_")[0] if "_" in h5tk else h5tk
