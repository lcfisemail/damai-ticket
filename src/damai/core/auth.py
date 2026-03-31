"""登录认证管理器。"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import unquote

import httpx
from cryptography.fernet import Fernet
from loguru import logger

from damai.constants import DEFAULT_HEADERS
from damai.exceptions import AuthError, LoginRequired


REQUIRED_COOKIE_FIELDS = ("_m_h5_tk", "_m_h5_tk_enc")
RECOMMENDED_COOKIE_FIELDS = ("cookie2", "t", "cna", "unb", "sgcookie")

_COOKIE_HEADER_PATTERN = re.compile(r"(?im)^\s*cookie\s*:\s*(.+)$")
_HEADER_ARGUMENT_PATTERN = re.compile(
    r"--header\s+(?:\"([^\"]+)\"|'([^']+)')",
    re.IGNORECASE,
)
_COOKIE_ARGUMENT_PATTERN = re.compile(
    r"(?:--cookie|-b)\s+(?:\"([^\"]+)\"|'([^']+)'|([^\s]+))",
    re.IGNORECASE,
)
_DOCUMENT_COOKIE_PATTERN = re.compile(
    r"document\.cookie\s*=\s*(?:\"([^\"]+)\"|'([^']+)')",
    re.IGNORECASE,
)


@dataclass(slots=True)
class CookieImportResult:
    cookies: dict[str, str]
    missing_required: list[str]
    missing_recommended: list[str]

    @property
    def normalized_cookie_string(self) -> str:
        return build_cookie_string(self.cookies)


@dataclass(slots=True)
class AccountProfile:
    display_name: str = ""
    user_id: str = ""


def build_cookie_string(cookies: dict[str, str]) -> str:
    return "; ".join(f"{key}={value}" for key, value in cookies.items())


def extract_account_profile(cookies: dict[str, str]) -> AccountProfile:
    raw_name = (
        cookies.get("damai.cn_nickName")
        or cookies.get("damai_cn_nickName")
        or cookies.get("nickName")
        or ""
    )
    display_name = unquote(raw_name).strip()
    user_id = (
        cookies.get("user_id")
        or cookies.get("munb")
        or cookies.get("unb")
        or ""
    ).strip()
    return AccountProfile(display_name=display_name, user_id=user_id)


def _parse_cookie_json(text: str) -> dict[str, str]:
    stripped = text.strip()
    if not stripped or stripped[0] not in "[{":
        return {}

    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return {}

    cookies: dict[str, str] = {}

    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict) and "name" in item and "value" in item:
                cookies[str(item["name"])] = str(item["value"])
        return cookies

    if not isinstance(payload, dict):
        return {}

    cookie_items = payload.get("cookies")
    if isinstance(cookie_items, list):
        for item in cookie_items:
            if isinstance(item, dict) and "name" in item and "value" in item:
                cookies[str(item["name"])] = str(item["value"])

    if cookies:
        return cookies

    if payload and all(isinstance(value, str) for value in payload.values()):
        return {str(key): value for key, value in payload.items()}

    return {}


def _parse_cookie_string(cookie_str: str) -> dict[str, str]:
    """解析标准 Cookie 字符串。"""
    normalized = cookie_str.strip().strip("\"'")
    if not normalized:
        return {}

    if normalized.lower().startswith("cookie:"):
        normalized = normalized.split(":", 1)[1].strip()

    normalized = normalized.replace("\r", "\n")
    normalized = "; ".join(
        segment.strip() for segment in normalized.splitlines() if segment.strip()
    )

    cookie_jar = SimpleCookie()
    try:
        cookie_jar.load(normalized)
    except Exception:
        cookie_jar = SimpleCookie()

    if cookie_jar:
        return {key: morsel.value for key, morsel in cookie_jar.items()}

    cookies: dict[str, str] = {}
    for part in normalized.split(";"):
        item = part.strip()
        if "=" not in item:
            continue
        key, _, value = item.partition("=")
        key = key.strip()
        value = value.strip()
        if key:
            cookies[key] = value
    return cookies


def _iter_cookie_candidates(text: str):
    stripped = text.strip()
    if not stripped:
        return

    for match in _COOKIE_HEADER_PATTERN.finditer(stripped):
        yield match.group(1).strip()

    for match in _HEADER_ARGUMENT_PATTERN.finditer(stripped):
        header_value = next(group for group in match.groups() if group)
        if ":" not in header_value:
            continue
        header_name, header_content = header_value.split(":", 1)
        if header_name.strip().lower() == "cookie":
            yield header_content.strip()

    for match in _COOKIE_ARGUMENT_PATTERN.finditer(stripped):
        yield next(group for group in match.groups() if group).strip()

    for match in _DOCUMENT_COOKIE_PATTERN.finditer(stripped):
        yield next(group for group in match.groups() if group).strip()

    lower_text = stripped.lower()
    if any(token in lower_text for token in ("cookie:", "_m_h5_tk=", "cookie2=")):
        yield stripped


def analyze_cookie_text(text: str) -> CookieImportResult:
    cookies: dict[str, str] = {}

    cookies.update(_parse_cookie_json(text))

    for candidate in _iter_cookie_candidates(text):
        cookies.update(_parse_cookie_string(candidate))

    if not cookies and ";" in text and "=" in text:
        cookies.update(_parse_cookie_string(text))

    missing_required = [field for field in REQUIRED_COOKIE_FIELDS if not cookies.get(field)]
    missing_recommended = [
        field for field in RECOMMENDED_COOKIE_FIELDS if not cookies.get(field)
    ]
    return CookieImportResult(
        cookies=cookies,
        missing_required=missing_required,
        missing_recommended=missing_recommended,
    )


class Account:
    """表示一个已登录的大麦账号。"""

    def __init__(
        self,
        nickname: str,
        session: httpx.AsyncClient,
        cookies: dict[str, str],
    ):
        self.nickname = nickname
        self.session = session
        self.cookies = cookies
        self.profile = extract_account_profile(cookies)
        self.logged_in = True
        self.login_time = time.time()

    @property
    def is_session_valid(self) -> bool:
        return self.logged_in and (time.time() - self.login_time < 7200)


class AuthManager:
    """认证管理器。"""

    _KEY_FILE = ".fernet.key"

    def __init__(self, data_dir: Path = Path("./data")):
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._fernet = self._load_or_create_fernet()

    def _load_or_create_fernet(self) -> Fernet:
        key_path = self._data_dir / self._KEY_FILE
        if key_path.exists():
            key = key_path.read_bytes()
        else:
            key = Fernet.generate_key()
            key_path.write_bytes(key)
            logger.debug("已生成新的加密密钥")
        return Fernet(key)

    def _encrypt(self, data: dict) -> bytes:
        return self._fernet.encrypt(json.dumps(data).encode())

    def _decrypt(self, data: bytes) -> dict:
        return json.loads(self._fernet.decrypt(data).decode())

    def save_cookies(self, nickname: str, cookies: dict[str, str]) -> None:
        path = self._data_dir / f"cookies_{nickname}.enc"
        path.write_bytes(self._encrypt(cookies))
        logger.debug(f"Cookie 已保存: {nickname}")

    def load_cookies(self, nickname: str) -> Optional[dict[str, str]]:
        path = self._data_dir / f"cookies_{nickname}.enc"
        if not path.exists():
            return None
        try:
            return self._decrypt(path.read_bytes())
        except Exception as error:
            logger.warning(f"Cookie 解密失败: {error}")
            return None

    async def login_by_cookie(
        self,
        cookie_string: str,
        nickname: str = "default",
    ) -> Account:
        parsed = analyze_cookie_text(cookie_string)
        cookies = parsed.cookies
        if not cookies:
            raise AuthError("未识别到 Cookie，请粘贴 Cookie 头、完整请求头或 curl 文本")
        if parsed.missing_required:
            missing = ", ".join(parsed.missing_required)
            raise AuthError(f"Cookie 缺少必填字段: {missing}")
        if parsed.missing_recommended:
            logger.warning(
                "Cookie 缺少推荐字段: {}",
                ", ".join(parsed.missing_recommended),
            )

        session = self._build_session(cookies)
        account = Account(nickname=nickname, session=session, cookies=cookies)

        ok = await self.check_login_status(account)
        if not ok:
            raise AuthError("Cookie 已失效，请重新获取")

        self.save_cookies(nickname, cookies)
        logger.info(f"Cookie 登录成功: {account.nickname}")
        return account

    async def login_by_saved_cookie(self, nickname: str = "default") -> Account:
        cookies = self.load_cookies(nickname)
        if not cookies:
            raise LoginRequired(f"未找到账号 {nickname} 的保存 Cookie")

        session = self._build_session(cookies)
        account = Account(nickname=nickname, session=session, cookies=cookies)

        ok = await self.check_login_status(account)
        if not ok:
            raise AuthError(f"账号 {nickname} 的保存 Cookie 已失效，请重新登录")

        logger.info(f"从本地恢复登录: {account.nickname}")
        return account

    async def login_by_qrcode(
        self,
        on_qr_ready: Callable[[str], None],
        nickname: str = "default",
        timeout: float = 120.0,
    ) -> Account:
        raise AuthError("请使用图形界面中的“扫码登录”入口完成登录")

    async def check_login_status(self, account: Account) -> bool:
        if not all(account.cookies.get(field) for field in REQUIRED_COOKIE_FIELDS):
            logger.warning(f"账号 {account.nickname} 缺少关键 Cookie 字段")
            return False

        try:
            warmup_resp = await account.session.get(
                "https://m.damai.cn/",
                headers={
                    "User-Agent": DEFAULT_HEADERS["User-Agent"],
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": DEFAULT_HEADERS["Accept-Language"],
                    "Referer": "https://m.damai.cn/",
                },
                timeout=10.0,
            )
            final_url = str(warmup_resp.url).lower()
            if any(token in final_url for token in ("login", "passport.alibaba.com")):
                logger.warning(f"账号 {account.nickname} 被重定向到登录页")
                return False
            if "m.damai.cn" in final_url and warmup_resp.status_code < 400:
                return True
        except Exception as error:
            logger.debug(f"m.damai.cn 登录态预热失败: {error!r}")

        try:
            resp = await account.session.get(
                "https://id.damai.cn/userinfo.htm",
                headers={
                    "User-Agent": DEFAULT_HEADERS["User-Agent"],
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": DEFAULT_HEADERS["Accept-Language"],
                    "Referer": "https://www.damai.cn/",
                },
                timeout=10.0,
            )
            if "login" in str(resp.url).lower():
                logger.warning(f"账号 {account.nickname} 未登录")
                return False
            return resp.status_code < 400
        except Exception as error:
            logger.warning(f"登录状态检查失败: {error!r}")
            return False

    @staticmethod
    def _build_session(cookies: dict[str, str]) -> httpx.AsyncClient:
        jar = httpx.Cookies()
        for key, value in cookies.items():
            jar.set(key, value)
            jar.set(key, value, domain=".damai.cn")
            jar.set(key, value, domain=".m.damai.cn")
            jar.set(key, value, domain=".taobao.com")
            jar.set(key, value, domain=".alibaba.com")
            jar.set(key, value, domain=".passport.alibaba.com")
        return httpx.AsyncClient(
            cookies=jar,
            headers=DEFAULT_HEADERS,
            follow_redirects=True,
            http2=True,
        )

    def export_cookies_string(self, account: Account) -> str:
        return build_cookie_string(account.cookies)
