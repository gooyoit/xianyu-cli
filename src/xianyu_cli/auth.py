from __future__ import annotations

import asyncio
import json
import select
import sys
import time
from dataclasses import asdict, dataclass

from playwright.async_api import async_playwright

from .config import resolve_storage_state_path


@dataclass(slots=True)
class AuthState:
    state_path: str
    exists: bool
    logged_in: bool
    cookie_count: int
    goofish_cookie_count: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


AUTH_COOKIE_NAMES = {
    "cookie1",
    "cookie17",
    "lgc",
    "_nk_",
    "sgcookie",
    "unb",
    "tracknick",
    "uc1",
}

QR_LOGIN_URL = "https://www.goofish.com/"
PASSPORT_LOGIN_URL = (
    "https://passport.goofish.com/mini_login.htm"
    "?lang=zh_cn"
    "&appName=xianyu"
    "&appEntrance=web"
    "&styleType=vertical"
    "&bizParams="
    "&notLoadSsoView=false"
    "&notKeepLogin=false"
    "&isMobile=false"
    "&qrCodeFirst=true"
    "&stie=77"
)
QR_GENERATE_ENDPOINT = "/newlogin/qrcode/generate.do"
QR_QUERY_ENDPOINT = "/newlogin/qrcode/query.do"
QR_NEW = "NEW"
QR_SCANNED = "SCANED"
QR_CONFIRMED = "CONFIRMED"
QR_CANCELED = "CANCELED"
QR_EXPIRED = "EXPIRED"


def inspect_auth_state(path: str | None) -> AuthState:
    state_path = resolve_storage_state_path(path)
    if not state_path.exists():
        return AuthState(
            state_path=str(state_path),
            exists=False,
            logged_in=False,
            cookie_count=0,
            goofish_cookie_count=0,
        )

    payload = json.loads(state_path.read_text(encoding="utf-8"))
    cookies = payload.get("cookies", [])
    cookie_count = len(cookies) if isinstance(cookies, list) else 0
    goofish_cookies = [
        cookie
        for cookie in cookies
        if isinstance(cookie, dict) and "goofish.com" in str(cookie.get("domain", ""))
    ]
    goofish_cookie_count = len(goofish_cookies)
    return AuthState(
        state_path=str(state_path),
        exists=True,
        logged_in=has_login_markers(goofish_cookies),
        cookie_count=cookie_count,
        goofish_cookie_count=goofish_cookie_count,
    )


def _goofish_cookies(cookies: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        cookie
        for cookie in cookies
        if isinstance(cookie, dict) and "goofish.com" in str(cookie.get("domain", ""))
    ]


def _normalize_cookies(cookies: list[dict[str, object]]) -> list[dict[str, object]]:
    return [cookie for cookie in cookies if isinstance(cookie, dict)]


def _is_login_cookie(cookie: dict[str, object]) -> bool:
    return str(cookie.get("name", "")) in AUTH_COOKIE_NAMES


def has_login_markers(cookies: list[dict[str, object]]) -> bool:
    normalized = _normalize_cookies(cookies)
    relevant = _goofish_cookies(normalized)
    return any(_is_login_cookie(cookie) for cookie in relevant)


def _should_save_browser_login(
    cookies: list[dict[str, object]],
    *,
    enter_pressed: bool,
) -> bool:
    return enter_pressed or has_login_markers(cookies)


def _stdin_enter_pressed() -> bool:
    if not sys.stdin or sys.stdin.closed or not sys.stdin.isatty():
        return False
    ready, _, _ = select.select([sys.stdin], [], [], 0)
    if not ready:
        return False
    return sys.stdin.readline().strip() == ""


def _render_qr_half_blocks(matrix: list[list[bool]]) -> str:
    if not matrix:
        return ""

    lines: list[str] = []
    size = len(matrix)
    for row_idx in range(0, size, 2):
        line = ""
        for col_idx in range(size):
            top = matrix[row_idx][col_idx]
            bottom = matrix[row_idx + 1][col_idx] if row_idx + 1 < size else False
            if top and bottom:
                line += "█"
            elif top:
                line += "▀"
            elif bottom:
                line += "▄"
            else:
                line += " "
        lines.append(line)
    return "\n".join(lines)


def _display_qr_in_terminal(data: str) -> bool:
    try:
        import qrcode  # type: ignore[import-untyped]
    except ImportError:
        return False

    qr = qrcode.QRCode(border=4)
    qr.add_data(data)
    qr.make(fit=True)
    try:
        print(_render_qr_half_blocks(qr.get_matrix()))
    except UnicodeEncodeError:
        return False
    return True


def _extract_qr_code_content(payload: dict[str, object]) -> str:
    content = payload.get("content", {})
    if not isinstance(content, dict):
        return ""
    data = content.get("data", {})
    if not isinstance(data, dict):
        return ""
    return str(data.get("codeContent", "")).strip()


def _extract_qr_status(payload: dict[str, object]) -> str:
    content = payload.get("content", {})
    if not isinstance(content, dict):
        return ""
    data = content.get("data", {})
    if not isinstance(data, dict):
        return ""
    return str(data.get("qrCodeStatus", "")).strip().upper()


async def _wait_for_login_markers(
    context,
    *,
    timeout_seconds: int,
    urls: list[str],
) -> list[dict[str, object]]:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        cookies = await context.cookies(urls)
        if has_login_markers(cookies):
            return cookies
        await asyncio.sleep(1)
    return await context.cookies(urls)


async def login_with_terminal_qrcode(
    path: str | None,
    *,
    timeout_seconds: int,
) -> AuthState:
    state_path = resolve_storage_state_path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(locale="zh-CN", timezone_id="Asia/Shanghai")
        page = await context.new_page()

        state = {"last_status": "", "confirmed": False}

        async def on_response(response) -> None:
            if QR_QUERY_ENDPOINT not in response.url:
                return
            try:
                payload = await response.json()
            except Exception:
                return
            qr_status = _extract_qr_status(payload)
            if not qr_status or qr_status == state["last_status"]:
                return
            state["last_status"] = qr_status
            if qr_status == QR_SCANNED:
                print("二维码已扫码，请在闲鱼 App 中确认登录。")
            elif qr_status == QR_CONFIRMED:
                print("二维码已确认，正在等待登录态落地。")
                state["confirmed"] = True
            elif qr_status == QR_CANCELED:
                print("二维码登录已取消。")
            elif qr_status == QR_EXPIRED:
                print("二维码已过期。")

        page.on("response", on_response)

        try:
            async with page.expect_response(
                lambda response: QR_GENERATE_ENDPOINT in response.url,
                timeout=20_000,
            ) as qr_response_info:
                await page.goto(PASSPORT_LOGIN_URL, wait_until="domcontentloaded")

            qr_response = await qr_response_info.value
            qr_payload = await qr_response.json()
            qr_url = _extract_qr_code_content(qr_payload)
            if not qr_url:
                raise RuntimeError(f"未能从闲鱼二维码接口提取二维码内容: {qr_payload}")

            print("请使用闲鱼 App 扫描下方二维码登录：\n")
            if not _display_qr_in_terminal(qr_url):
                print("当前环境无法直接渲染终端二维码。请安装依赖：pip install qrcode")
                print(f"二维码链接: {qr_url}")
            print("\n等待扫码与确认...")

            deadline = time.time() + timeout_seconds
            while time.time() < deadline:
                if state["last_status"] == QR_EXPIRED:
                    raise TimeoutError("二维码已过期，请重新执行登录。")
                if state["last_status"] == QR_CANCELED:
                    raise RuntimeError("二维码登录已取消，请重新执行登录。")
                if state["confirmed"]:
                    break
                await asyncio.sleep(1)

            if not state["confirmed"]:
                raise TimeoutError(f"二维码登录等待超时，超过 {timeout_seconds} 秒。")

            cookies = await _wait_for_login_markers(
                context,
                timeout_seconds=20,
                urls=[QR_LOGIN_URL, "https://passport.goofish.com"],
            )
            if not has_login_markers(cookies):
                raise RuntimeError(
                    "二维码确认后，浏览器上下文中仍未拿到稳定登录 Cookie。"
                    "请重新执行 `xianyu login --qrcode` 再试。"
                )

            await context.storage_state(path=str(state_path))
        finally:
            await context.close()
            await browser.close()

    return inspect_auth_state(str(state_path))


async def login_with_browser(
    path: str | None,
    *,
    timeout_seconds: int,
    login_url: str = "https://www.goofish.com",
    qrcode: bool = False,
    auto_detect: bool = False,
) -> AuthState:
    state_path = resolve_storage_state_path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(QR_LOGIN_URL if qrcode else login_url, wait_until="domcontentloaded")

        if qrcode:
            print("浏览器已打开，请使用页面中的二维码登录闲鱼。")
        else:
            print("浏览器已打开，请在页面中完成闲鱼登录。")
        if auto_detect:
            print("检测到登录态后会自动保存，也可以回到终端按回车立即保存。")
        else:
            print("登录态出现后会自动保存，也可以回到终端按回车立即保存。")

        deadline = time.time() + timeout_seconds
        while True:
            if time.time() >= deadline:
                raise TimeoutError(f"登录等待超时，超过 {timeout_seconds} 秒。")

            cookies = await context.cookies([QR_LOGIN_URL, login_url])
            enter_pressed = False
            try:
                enter_pressed = _stdin_enter_pressed()
            except (OSError, ValueError):
                pass

            if _should_save_browser_login(
                cookies,
                enter_pressed=enter_pressed,
            ):
                if has_login_markers(cookies):
                    print("检测到登录态，正在保存。")
                elif enter_pressed:
                    print("收到手工确认，正在保存。")
                break

            await asyncio.sleep(1)

        await context.storage_state(path=str(state_path))
        await context.close()
        await browser.close()

    return inspect_auth_state(str(state_path))


def logout(path: str | None) -> bool:
    state_path = resolve_storage_state_path(path)
    if not state_path.exists():
        return False
    state_path.unlink()
    return True
