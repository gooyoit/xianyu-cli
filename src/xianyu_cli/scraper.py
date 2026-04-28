from __future__ import annotations

import asyncio
from collections.abc import Iterable
from urllib.parse import quote_plus

from playwright.async_api import Page, async_playwright

from .models import SearchItem, SearchOptions, SearchRunResult
from .parser import parse_search_api_payload

SEARCH_API_MARKER = "h5api.m.goofish.com/h5/mtop.taobao.idlemtopsearch.pc.search"
ILLEGAL_ACCESS_MARKER = "非法访问"

ANTI_DETECTION_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {
  get: () => undefined,
});
Object.defineProperty(navigator, 'languages', {
  get: () => ['zh-CN', 'zh', 'en-US', 'en'],
});
Object.defineProperty(navigator, 'plugins', {
  get: () => [1, 2, 3, 4, 5],
});
window.chrome = window.chrome || {
  runtime: {},
  app: {},
};
const originalQuery = window.navigator.permissions && window.navigator.permissions.query;
if (originalQuery) {
  window.navigator.permissions.query = (parameters) => (
    parameters && parameters.name === 'notifications'
      ? Promise.resolve({ state: Notification.permission })
      : originalQuery(parameters)
  );
}
"""


def _payload_requires_login(payload: dict) -> bool:
    ret = payload.get("ret", [])
    if isinstance(ret, list) and any("RGV587_ERROR::SM" in str(item) for item in ret):
        return True

    data = payload.get("data", {})
    login_url = ""
    if isinstance(data, dict):
        login_url = str(data.get("url", "")) or str(data.get("h5url", ""))
    return "passport.goofish.com/mini_login" in login_url


async def _apply_sort(page: Page, sort: str) -> None:
    if sort != "latest":
        return
    try:
        await page.get_by_text("新发布").click(timeout=5_000)
        await page.get_by_text("最新").click(timeout=5_000)
    except Exception:
        # Sorting controls are not always rendered for anonymous sessions.
        return


def _dedupe_items(items: Iterable[SearchItem]) -> list[SearchItem]:
    seen: set[str] = set()
    unique: list[SearchItem] = []
    for item in items:
        key = item.item_id or item.link
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


async def scrape_keyword(keyword: str, options: SearchOptions) -> SearchRunResult:
    captured: list[SearchItem] = []
    raw_payloads: list[dict] = []

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=options.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--disable-dev-shm-usage",
            ],
        )
        context_kwargs = {
            "user_agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "locale": "zh-CN",
            "timezone_id": "Asia/Shanghai",
            "viewport": {"width": 1440, "height": 900},
        }
        if options.storage_state:
            context_kwargs["storage_state"] = options.storage_state
        context = await browser.new_context(**context_kwargs)
        await context.add_init_script(ANTI_DETECTION_SCRIPT)
        page = await context.new_page()
        page.set_default_timeout(options.navigation_timeout_ms)

        async def on_response(response) -> None:
            if SEARCH_API_MARKER not in response.url:
                return
            try:
                payload = await response.json()
            except Exception:
                return
            raw_payloads.append(payload)
            captured.extend(parse_search_api_payload(payload, keyword))

        page.on("response", on_response)

        try:
            search_url = f"https://www.goofish.com/search?q={quote_plus(keyword)}"
            await page.goto(search_url, wait_until="domcontentloaded")
            await asyncio.sleep(options.min_wait_ms / 1000)

            body_text = await page.locator("body").inner_text()
            if ILLEGAL_ACCESS_MARKER in body_text:
                raise RuntimeError(
                    "闲鱼返回“非法访问”。当前浏览器环境被风控拦截，"
                    "请先尝试 `xianyu search ... --headful` 或重新登录后再试。"
                )

            await _apply_sort(page, options.sort)

            current_page = 1
            while current_page < options.page:
                next_button = page.locator(
                    "[class*='search-pagination-arrow-right']:not([disabled])"
                )
                if await next_button.count() == 0:
                    break
                if current_page + 1 == options.page:
                    captured.clear()
                    raw_payloads.clear()
                await next_button.click()
                current_page += 1
                await asyncio.sleep(options.min_wait_ms / 1000)

            fetched_pages = 1
            while fetched_pages < options.pages:
                next_button = page.locator(
                    "[class*='search-pagination-arrow-right']:not([disabled])"
                )
                if await next_button.count() == 0:
                    break
                await next_button.click()
                fetched_pages += 1
                await asyncio.sleep(options.min_wait_ms / 1000)

            await asyncio.sleep(options.min_wait_ms / 1000)
        finally:
            await context.close()
            await browser.close()

    items = _dedupe_items(captured) if options.dedupe else captured
    if options.max_items is not None:
        items = items[: options.max_items]

    if not items and any(_payload_requires_login(payload) for payload in raw_payloads):
        raise RuntimeError(
            "闲鱼搜索接口要求登录校验，当前保存的会话还不能直接搜索。"
            "请重新执行 `xianyu login --qrcode`，确认浏览器里已经真正登录成功后再回终端保存。"
        )

    return SearchRunResult(keyword=keyword, items=items, raw_payloads=raw_payloads)


async def scrape_all(options: SearchOptions) -> list[SearchRunResult]:
    results: list[SearchRunResult] = []
    for keyword in options.keywords:
        results.append(await scrape_keyword(keyword, options))
    return results
