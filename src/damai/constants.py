"""大麦网 mTOP 协议常量"""

# mTOP 网关
MTOP_BASE_URL = "https://mtop.damai.cn/gw/"
MTOP_H5_APP_KEY = "12574478"
MTOP_JSV = "2.7.2"

# 大麦网域名
DAMAI_HOST = "https://www.damai.cn"
DAMAI_M_HOST = "https://m.damai.cn"

# API 名称
API_DETAIL = "mtop.alibaba.damai.detail.getdetail"
API_SUBPAGE = "mtop.alibaba.detail.subpage.getdetail"
API_ORDER_BUILD = "mtop.trade.order.build.h5"
API_ORDER_CREATE = "mtop.trade.order.create.h5"
API_BUY_INFO = "mtop.alibaba.damai.buy.buyinfo.get"

# 默认请求头
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Origin": "https://m.damai.cn",
    "Referer": "https://m.damai.cn/",
    "Content-Type": "application/x-www-form-urlencoded",
    "X-Requested-With": "XMLHttpRequest",
}

# mTOP 响应成功码前缀
MTOP_SUCCESS_CODE = "SUCCESS::"

# mTOP 特定错误码
MTOP_ERR_TOKEN_EXPIRED = "FAIL_SYS_TOKEN_EXOIRED"
MTOP_ERR_TRAFFIC_LIMIT = "FAIL_SYS_TRAFFIC_LIMIT"
MTOP_ERR_CAPTCHA = "RGV587_ERROR"
MTOP_ERR_SESSION_EXPIRED = "FAIL_SYS_SESSION_EXPIRED"
