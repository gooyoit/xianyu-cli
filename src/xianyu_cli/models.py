from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass(slots=True)
class SearchItem:
    keyword: str
    title: str
    price: str
    area: str
    seller: str
    link: str
    image_url: str
    publish_time: str
    item_id: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(slots=True)
class SearchOptions:
    keywords: list[str]
    pages: int
    sort: str
    headless: bool
    output_format: str
    output_path: str | None
    storage_state: str | None
    storage_state_explicit: bool
    min_wait_ms: int
    navigation_timeout_ms: int
    max_items: int | None
    dedupe: bool
    pretty: bool
    dry_run: bool
    raw_json: bool

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["generated_at"] = datetime.now().isoformat(timespec="seconds")
        return data


@dataclass(slots=True)
class SearchRunResult:
    keyword: str
    items: list[SearchItem]
    raw_payloads: list[dict]

    def to_dict(self) -> dict[str, object]:
        return {
            "keyword": self.keyword,
            "items": [item.to_dict() for item in self.items],
            "raw_payloads": self.raw_payloads,
        }
