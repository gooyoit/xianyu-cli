from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from .auth import inspect_auth_state, login_with_browser, login_with_terminal_qrcode, logout
from .config import get_default_storage_state_path
from .exporters import serialize_items, write_output
from .models import SearchOptions
from .scraper import scrape_all


def configure_output_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(errors="replace")
        except (AttributeError, OSError, ValueError):
            continue


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="xianyu", description="Xianyu CLI search tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    search = subparsers.add_parser("search", help="Search Xianyu listings")
    search.add_argument("keywords", nargs="*", help="Keyword list")
    search.add_argument("-k", "--keyword", action="append", default=[], help="Repeatable keyword")
    search.add_argument("--keyword-file", help="Read one keyword per line")
    search.add_argument("--pages", type=int, default=1, help="Maximum pages per keyword")
    search.add_argument("--page", type=int, default=1, help="Start page number")
    search.add_argument(
        "--sort",
        choices=["default", "latest"],
        default="latest",
        help="Result sort mode",
    )
    search.add_argument(
        "--format",
        dest="output_format",
        choices=["table", "json", "ndjson", "csv"],
        default="table",
        help="Output format",
    )
    search.add_argument("-o", "--output", help="Write results to file")
    search.add_argument("--storage-state", help="Playwright storage state JSON file")
    search.add_argument("--headful", action="store_true", help="Run browser in visible mode")
    search.add_argument("--min-wait-ms", type=int, default=1200, help="Wait after page actions")
    search.add_argument(
        "--navigation-timeout-ms",
        type=int,
        default=20_000,
        help="Playwright timeout in milliseconds",
    )
    search.add_argument("--max-items", type=int, help="Limit returned items")
    search.add_argument("--no-dedupe", action="store_true", help="Disable item dedupe")
    search.add_argument("--compact", action="store_true", help="Disable pretty JSON output")
    search.add_argument("--json", action="store_true", help="Print raw search API payloads as JSON")
    search.add_argument("--dry-run", action="store_true", help="Validate arguments only")
    search.set_defaults(handler=run_search)

    login = subparsers.add_parser("login", help="Open browser and save Xianyu login state")
    login.add_argument("--storage-state", help="Path to save Playwright storage state")
    login.add_argument(
        "--timeout-seconds",
        type=int,
        default=300,
        help="Maximum wait time for manual login",
    )
    login.add_argument(
        "--qrcode",
        action="store_true",
        help="Render QR in terminal and complete login automatically",
    )
    login.add_argument(
        "--auto-detect",
        action="store_true",
        help="Auto-save when strong auth cookies are detected",
    )
    login.set_defaults(handler=run_login)

    status = subparsers.add_parser("status", help="Show saved login state summary")
    status.add_argument("--storage-state", help="Path to Playwright storage state")
    status.set_defaults(handler=run_status)

    logout_cmd = subparsers.add_parser("logout", help="Delete saved login state")
    logout_cmd.add_argument("--storage-state", help="Path to Playwright storage state")
    logout_cmd.set_defaults(handler=run_logout)
    return parser


def _load_keywords(args: argparse.Namespace) -> list[str]:
    keywords = list(args.keywords) + list(args.keyword)
    if args.keyword_file:
        file_keywords = [
            line.strip()
            for line in Path(args.keyword_file).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        keywords.extend(file_keywords)

    deduped: list[str] = []
    seen: set[str] = set()
    for keyword in keywords:
        if keyword not in seen:
            deduped.append(keyword)
            seen.add(keyword)
    return deduped


def parse_options(args: argparse.Namespace) -> SearchOptions:
    keywords = _load_keywords(args)
    if not keywords:
        raise SystemExit("至少要提供一个关键词，可以用位置参数、--keyword 或 --keyword-file。")
    if args.pages < 1:
        raise SystemExit("--pages 必须 >= 1")
    if args.page < 1:
        raise SystemExit("--page 必须 >= 1")
    if args.min_wait_ms < 0:
        raise SystemExit("--min-wait-ms 必须 >= 0")
    if args.navigation_timeout_ms < 1:
        raise SystemExit("--navigation-timeout-ms 必须 >= 1")
    if args.max_items is not None and args.max_items < 1:
        raise SystemExit("--max-items 必须 >= 1")

    resolved_state = args.storage_state
    default_state = get_default_storage_state_path()
    if not resolved_state and default_state.exists():
        resolved_state = str(default_state)

    return SearchOptions(
        keywords=keywords,
        page=args.page,
        pages=args.pages,
        sort=args.sort,
        headless=not args.headful,
        output_format=args.output_format,
        output_path=args.output,
        storage_state=resolved_state,
        storage_state_explicit=bool(args.storage_state),
        min_wait_ms=args.min_wait_ms,
        navigation_timeout_ms=args.navigation_timeout_ms,
        max_items=args.max_items,
        dedupe=not args.no_dedupe,
        pretty=not args.compact,
        dry_run=args.dry_run,
        raw_json=args.json,
    )


async def run_login(args: argparse.Namespace) -> int:
    if args.timeout_seconds < 1:
        raise SystemExit("--timeout-seconds 必须 >= 1")
    if args.qrcode:
        state = await login_with_terminal_qrcode(
            args.storage_state,
            timeout_seconds=args.timeout_seconds,
        )
    else:
        state = await login_with_browser(
            args.storage_state,
            timeout_seconds=args.timeout_seconds,
            qrcode=False,
            auto_detect=args.auto_detect,
        )
    print(
        json.dumps(
            state.to_dict(),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def run_status(args: argparse.Namespace) -> int:
    state = inspect_auth_state(args.storage_state)
    print(_format_status_output(state.to_dict()))
    return 0 if state.logged_in else 1


def _format_status_output(state: dict[str, object]) -> str:
    ok = bool(state["logged_in"])
    error_message = "Status check failed: Session expired - please re-login with: xianyu login"
    lines = [
        f"ok: {str(ok).lower()}",
        "schema_version: '1'",
        "state:",
    ]
    for key, value in state.items():
        lines.append(f"  {key}: {_format_yaml_scalar(value)}")

    if not ok:
        lines.extend(
            [
                "error:",
                "  code: not_authenticated",
                f"  message: '{error_message}'",
            ]
        )
    return "\n".join(lines)


def _format_yaml_scalar(value: object) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int):
        return str(value)
    if value is None:
        return "null"
    return "'" + str(value).replace("'", "''") + "'"


def run_logout(args: argparse.Namespace) -> int:
    removed = logout(args.storage_state)
    print(
        json.dumps(
            {
                "logged_out": removed,
                "state_path": str(args.storage_state or get_default_storage_state_path()),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


async def run_search(args: argparse.Namespace) -> int:
    options = parse_options(args)
    if options.dry_run:
        print(json.dumps(options.to_dict(), ensure_ascii=False, indent=2))
        return 0

    results = await scrape_all(options)
    items = [item for result in results for item in result.items]
    raw_response = {
        "keywords": options.keywords,
        "responses": [
            {
                "keyword": result.keyword,
                "payloads": result.raw_payloads,
            }
            for result in results
        ],
    }

    if options.raw_json:
        output = json.dumps(raw_response, ensure_ascii=False, indent=2 if options.pretty else None)
        if options.output_path:
            Path(options.output_path).write_text(output, encoding="utf-8")
            print(f"已写入原始接口响应到 {options.output_path}")
            return 0
        print(output)
        return 0

    if options.output_path:
        write_output(
            items,
            output_format=options.output_format,
            path=options.output_path,
            pretty=options.pretty,
        )
        print(f"已写入 {len(items)} 条结果到 {options.output_path}")
        return 0

    if options.output_format == "csv":
        raise SystemExit("CSV 输出需要配合 --output 指定文件路径。")

    print(serialize_items(items, output_format=options.output_format, pretty=options.pretty))
    return 0


def main(argv: list[str] | None = None) -> int:
    configure_output_encoding()
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = args.handler
    result = handler(args)
    if asyncio.iscoroutine(result):
        return asyncio.run(result)
    return int(result)


if __name__ == "__main__":
    sys.exit(main())
