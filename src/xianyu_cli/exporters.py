from __future__ import annotations

import csv
import json
from pathlib import Path

from .models import SearchItem

TABLE_HEADERS = [
    "keyword",
    "title",
    "price",
    "area",
    "seller",
    "publish_time",
    "link",
]


def render_table(items: list[SearchItem]) -> str:
    rows = [TABLE_HEADERS]
    for item in items:
        rows.append(
            [
                item.keyword,
                item.title,
                item.price,
                item.area,
                item.seller,
                item.publish_time,
                item.link,
            ]
        )

    widths = [max(len(str(row[i])) for row in rows) for i in range(len(TABLE_HEADERS))]

    def fmt(row: list[str]) -> str:
        return " | ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row))

    divider = "-+-".join("-" * width for width in widths)
    output = [fmt(rows[0]), divider]
    output.extend(fmt([str(cell) for cell in row]) for row in rows[1:])
    return "\n".join(output)


def serialize_items(items: list[SearchItem], output_format: str, pretty: bool) -> str:
    data = [item.to_dict() for item in items]
    if output_format == "json":
        return json.dumps(data, ensure_ascii=False, indent=2 if pretty else None)
    if output_format == "ndjson":
        return "\n".join(
            json.dumps(row, ensure_ascii=False) for row in data
        )
    if output_format == "table":
        return render_table(items)
    raise ValueError(f"Unsupported format for direct serialization: {output_format}")


def write_output(
    items: list[SearchItem],
    output_format: str,
    path: str,
    pretty: bool,
) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    if output_format == "csv":
        with destination.open("w", encoding="utf-8", newline="") as handle:
            fieldnames = (
                list(items[0].to_dict().keys())
                if items
                else [
                    "keyword",
                    "title",
                    "price",
                    "area",
                    "seller",
                    "link",
                    "image_url",
                    "publish_time",
                    "item_id",
                ]
            )
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for item in items:
                writer.writerow(item.to_dict())
        return

    destination.write_text(
        serialize_items(items, output_format=output_format, pretty=pretty),
        encoding="utf-8",
    )
