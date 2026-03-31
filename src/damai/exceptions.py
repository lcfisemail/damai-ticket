"""自定义异常层级"""


class DamaiError(Exception):
    """基础异常"""


class AuthError(DamaiError):
    """认证相关异常"""


class LoginRequired(AuthError):
    """需要登录"""


class TokenExpiredError(AuthError):
    """Token已过期，需要刷新"""


class MtopError(DamaiError):
    """mTOP协议相关异常"""

    def __init__(self, message: str, ret_codes: list[str] | None = None):
        super().__init__(message)
        self.ret_codes = ret_codes or []


class TrafficLimitError(MtopError):
    """请求被限流"""


class CaptchaRequiredError(MtopError):
    """需要验证码"""

    def __init__(self, message: str, captcha_data: dict | None = None):
        super().__init__(message)
        self.captcha_data = captcha_data or {}


class OrderError(DamaiError):
    """下单相关异常"""


class SoldOutError(OrderError):
    """票档售罄"""


class OrderBuildError(OrderError):
    """构建订单失败"""


class OrderCreateError(OrderError):
    """创建订单失败"""


class ConfigError(DamaiError):
    """配置相关异常"""


class ProxyError(DamaiError):
    """代理相关异常"""
