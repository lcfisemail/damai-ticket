"""演出详情加载与解析。"""
from __future__ import annotations

from typing import Any

from damai.constants import API_DETAIL
from damai.core.mtop_client import MtopClient


def _get_nested(data: dict[str, Any], *path: str) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _pick_first(data: dict[str, Any], paths: list[tuple[str, ...]], default: str = "") -> str:
    for path in paths:
        value = _get_nested(data, *path)
        if value in (None, ""):
            continue
        return str(value)
    return default


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text


def _build_session_label(session: dict[str, Any]) -> str:
    name = _normalize_text(session.get("performName"))
    start_time = _pick_first(
        session,
        [
            ("performBeginDTStr",),
            ("performBeginTimeStr",),
            ("performBeginDT",),
            ("showTime",),
            ("startTime",),
        ],
    )
    if start_time and start_time not in name:
        return f"{name}（{start_time}）" if name else start_time
    return name or start_time or "未命名场次"


def _build_tier_label(tier: dict[str, Any]) -> str:
    name = _normalize_text(tier.get("priceName")) or "未命名票档"
    price = tier.get("price")
    if isinstance(price, int) and price > 0:
        return f"{name}（¥{price / 100:.2f}）"
    return name


def parse_event_detail(item_id: str, detail: dict[str, Any]) -> dict[str, Any]:
    perform = detail.get("perform", {})
    sessions = perform.get("performs", [])

    title = _pick_first(
        detail,
        [
            ("itemBasicInfo", "name"),
            ("itemBasicInfo", "itemName"),
            ("item", "name"),
            ("perform", "name"),
            ("perform", "itemName"),
        ],
        default=_normalize_text(perform.get("name")),
    )
    status = _pick_first(
        detail,
        [
            ("perform", "performStatus", "name"),
            ("perform", "itemStatusName"),
            ("perform", "statusName"),
        ],
    )
    venue = _pick_first(
        detail,
        [
            ("perform", "venueName"),
            ("itemBasicInfo", "venueName"),
            ("venue", "name"),
        ],
    )
    city = _pick_first(
        detail,
        [
            ("perform", "cityName"),
            ("itemBasicInfo", "cityName"),
            ("venue", "cityName"),
        ],
    )

    session_items: list[dict[str, Any]] = []
    tier_items: list[dict[str, Any]] = []
    seen_tier_names: set[str] = set()

    for session in sessions:
        session_name = _normalize_text(session.get("performName"))
        session_items.append(
            {
                "id": _normalize_text(session.get("performId")),
                "name": session_name,
                "label": _build_session_label(session),
                "time": _pick_first(
                    session,
                    [
                        ("performBeginDTStr",),
                        ("performBeginTimeStr",),
                        ("performBeginDT",),
                        ("showTime",),
                        ("startTime",),
                    ],
                ),
            }
        )

        for tier in session.get("priceList", []):
            tier_name = _normalize_text(tier.get("priceName"))
            if not tier_name or tier_name in seen_tier_names:
                continue
            seen_tier_names.add(tier_name)
            tier_items.append(
                {
                    "id": _normalize_text(tier.get("priceId")),
                    "name": tier_name,
                    "label": _build_tier_label(tier),
                    "price": tier.get("price", 0),
                }
            )

    return {
        "item_id": item_id,
        "title": title or f"演出 {item_id}",
        "status": status,
        "venue": venue,
        "city": city,
        "session_count": len(session_items),
        "tier_count": len(tier_items),
        "sessions": session_items,
        "tiers": tier_items,
    }


async def fetch_event_detail(client: MtopClient, item_id: str) -> dict[str, Any]:
    resp = await client.execute(API_DETAIL, "1.0", {"itemId": item_id})
    if not resp.is_success:
        error_text = "; ".join(resp.error_codes) or "未知错误"
        raise RuntimeError(f"加载演出详情失败: {error_text}")

    detail = resp.data.get("detail", {})
    if not detail:
        raise RuntimeError("未返回演出详情数据")
    return parse_event_detail(item_id=item_id, detail=detail)
