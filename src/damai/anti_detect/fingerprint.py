"""设备指纹生成与持久化"""
import base64
import json
import random
import string
import time
from pathlib import Path
from typing import Optional

from loguru import logger


def _random_base64(length: int) -> str:
    """生成随机 base64 字符串"""
    raw = bytes(random.getrandbits(8) for _ in range(length))
    return base64.b64encode(raw).decode("ascii")


def _random_hex(length: int) -> str:
    return "".join(random.choices("0123456789abcdef", k=length))


def generate_utdid() -> str:
    """
    生成阿里 utdid（设备唯一标识）
    格式: 24字符 base64-like 字符串
    """
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=24))


def generate_did() -> str:
    """生成设备ID，格式类似 UUID"""
    return (
        f"{_random_hex(8)}-{_random_hex(4)}-"
        f"{_random_hex(4)}-{_random_hex(4)}-{_random_hex(12)}"
    )


def generate_umid_token(utdid: str) -> str:
    """生成 umidToken（基于 utdid 的设备令牌）"""
    ts = str(int(time.time()))
    raw = f"{utdid}{ts}"
    encoded = base64.b64encode(raw.encode()).decode()
    return encoded[:32]


class DeviceFingerprint:
    """
    设备指纹，每个账号绑定一个指纹并持久化，
    避免每次运行生成新指纹（频繁变更本身是异常信号）。
    """

    def __init__(
        self,
        utdid: Optional[str] = None,
        did: Optional[str] = None,
        umid_token: Optional[str] = None,
    ):
        self.utdid = utdid or generate_utdid()
        self.did = did or generate_did()
        self.umid_token = umid_token or generate_umid_token(self.utdid)

    def to_dict(self) -> dict:
        return {
            "utdid": self.utdid,
            "did": self.did,
            "umid_token": self.umid_token,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DeviceFingerprint":
        return cls(
            utdid=data.get("utdid"),
            did=data.get("did"),
            umid_token=data.get("umid_token"),
        )

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f)

    @classmethod
    def load_or_create(cls, path: str | Path) -> "DeviceFingerprint":
        """从文件加载，不存在则生成新指纹并保存"""
        path = Path(path)
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                fp = cls.from_dict(data)
                logger.debug(f"已加载设备指纹: utdid={fp.utdid[:8]}...")
                return fp
            except Exception as e:
                logger.warning(f"加载指纹失败，重新生成: {e}")
        fp = cls()
        fp.save(path)
        logger.debug(f"已生成新设备指纹: utdid={fp.utdid[:8]}...")
        return fp
