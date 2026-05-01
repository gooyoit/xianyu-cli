from __future__ import annotations

import json
from pathlib import Path

from xianyu_cli.parser import normalize_price, parse_search_api_payload


def test_normalize_price_supports_wan_unit() -> None:
    assert normalize_price([{"text": "当前价"}, {"text": "¥1.2万"}]) == "¥12000"


def test_parse_search_api_payload_maps_reference_shape() -> None:
    payload = json.loads(
        Path("tests/fixtures/search_payload.json").read_text(encoding="utf-8")
    )
    items = parse_search_api_payload(payload, keyword="macbook")

    assert len(items) == 2
    assert items[0].title == "MacBook Pro 14"
    assert items[0].link == "https://h5.m.goofish.com/item?id=123456"
    assert items[0].image_url == "https://img.alicdn.com/example.jpg"
    assert items[1].price == "¥12000"
    assert items[1].item_id == "654321"
