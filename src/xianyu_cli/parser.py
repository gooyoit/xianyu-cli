from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import SearchItem


def safe_get(data: Any, *keys: Any, default: Any = "") -> Any:
    for key in keys:
        try:
            data = data[key]
        except (KeyError, TypeError, IndexError):
            return default
    return data


def normalize_price(price_parts: Any) -> str:
    if not isinstance(price_parts, list):
        return "价格异常"

    text = "".join(
        str(part.get("text", ""))
        for part in price_parts
        if isinstance(part, dict)
    ).replace("当前价", "").strip()

    if not text:
        return "价格异常"

    if "万" in text:
        raw = text.replace("¥", "").replace("万", "").strip()
        try:
            return f"¥{float(raw) * 10000:.0f}"
        except ValueError:
            return text

    return text


def normalize_link(raw_link: str) -> str:
    if not raw_link:
        return ""
    return raw_link.replace("fleamarket://", "https://www.goofish.com/")


def normalize_image_url(image_url: str) -> str:
    if not image_url:
        return ""
    if image_url.startswith("http://") or image_url.startswith("https://"):
        return image_url
    if image_url.startswith("//"):
        return f"https:{image_url}"
    return image_url


def normalize_publish_time(raw_value: Any) -> str:
    text = str(raw_value or "")
    if not text.isdigit():
        return "未知时间"
    return datetime.fromtimestamp(int(text) / 1000).strftime("%Y-%m-%d %H:%M")


def parse_search_api_payload(payload: dict[str, Any], keyword: str) -> list[SearchItem]:
    items = payload.get("data", {}).get("resultList", [])
    parsed: list[SearchItem] = []

    for item in items:
        main_data = safe_get(item, "data", "item", "main", "exContent", default={})
        click_args = safe_get(
            item,
            "data",
            "item",
            "main",
            "clickParam",
            "args",
            default={},
        )
        item_id = str(safe_get(click_args, "item_id", default=""))
        parsed.append(
            SearchItem(
                keyword=keyword,
                title=safe_get(main_data, "title", default="未知标题"),
                price=normalize_price(safe_get(main_data, "price", default=[])),
                area=safe_get(main_data, "area", default="地区未知"),
                seller=safe_get(main_data, "userNickName", default="匿名卖家"),
                link=normalize_link(
                    safe_get(item, "data", "item", "main", "targetUrl", default="")
                ),
                image_url=normalize_image_url(
                    safe_get(main_data, "picUrl", default="")
                ),
                publish_time=normalize_publish_time(
                    safe_get(click_args, "publishTime", default="")
                ),
                item_id=item_id,
            )
        )

    return parsed
