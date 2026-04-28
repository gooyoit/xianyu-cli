# xianyu-cli

English | [中文](./README.zh-CN.md)

A CLI for Xianyu (闲鱼 / Goofish) — search listings and capture raw search responses with Playwright.

## Disclaimer

This project is created and shared purely for personal interest, learning, and technical research.

- It must not be used for commercial purposes, profit-making activities, large-scale scraping, or any unlawful use.
- Any use of this project is at the user's own risk.
- The user is solely responsible for any direct or indirect consequences arising from the use of this project.
- The project author and contributors assume no responsibility or liability for any loss, damage, legal risk, account restriction, or other consequence caused by the use or misuse of this project.
- Technical discussion, learning, and collaborative research are welcome.

## Features

- 🔐 **Login** — browser-assisted login, saved session reuse, login status check, logout
- 🔍 **Search** — search by keyword, repeated keywords, or keyword file
- 📦 **Output formats** — `table`, `json`, `ndjson`, `csv`
- 🧾 **Raw API output** — `--json` returns captured search API payloads
- ♻️ **Session reuse** — automatically uses the saved Playwright storage state when available
- 🧹 **CLI-first design** — no FastAPI, no database

## Installation

```bash
# Recommended after publish
pip install xianyu-cli
playwright install chromium
```

From source:

```bash
git clone <your-repo-url>
cd xianyu-cli
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m playwright install chromium
```

## Usage

```bash
# ─── Login ────────────────────────────────────────
xianyu login                              # Open browser and save login state
xianyu login --qrcode                     # Render QR in terminal and complete login automatically
xianyu login --auto-detect                # Auto-save when strong auth cookies appear
xianyu status                             # Check saved login status
xianyu logout                             # Remove saved login state
xianyu login --storage-state ./state.json # Save to a custom path

# ─── Search ───────────────────────────────────────
xianyu search "iPhone 15"                 # Basic search
xianyu search "显卡" --pages 2            # Pagination
xianyu search "显卡" --page 3             # Fetch starting from page 3
xianyu search "显卡" --page 3 --pages 2   # Fetch 2 pages starting from page 3
xianyu search --keyword 显卡 --keyword 相机
xianyu search --keyword-file keywords.txt

# Structured output
xianyu search "显卡" --format json
xianyu search "显卡" --format ndjson
xianyu search "显卡" --format csv --output result.csv

# Raw search API payloads
xianyu search "显卡" --json
xianyu search "显卡" --json --output raw.json

# Parameter validation only
xianyu search "MacBook" --dry-run --format json
```

## Authentication

Anonymous sessions often return empty or incomplete results on Xianyu. You should usually log in before running live searches.

`xianyu login` opens a visible Chromium window. Complete the login in the browser, then return to the terminal and press Enter to save.

If you prefer terminal QR login, use:

```bash
xianyu login --qrcode
```

This mode keeps a Playwright browser context running in the background, renders the QR code directly in the terminal, polls the QR status, and saves the login state automatically after confirmation.

The CLI supports three login styles:

- manual confirm: default and recommended, press Enter in the terminal after login
- auto-detect: optional, use `xianyu login --auto-detect`
- terminal QR login: use `xianyu login --qrcode`

Saved login state path by default:

```bash
~/.config/xianyu-cli/storage-state.json
```

Once saved, later `xianyu search ...` commands automatically reuse that state.

If the browser used to close too early, that was caused by overly loose anonymous-cookie detection. The default login flow is now manual-save, which is more reliable.

## Search

Basic search:

```bash
xianyu search "iPhone 15"
```

Multiple keywords:

```bash
xianyu search "显卡" "机械键盘" "相机"
xianyu search --keyword 显卡 --keyword 机械键盘 --keyword 相机
xianyu search --keyword-file keywords.txt
```

Pagination:

```bash
xianyu search "显卡" --pages 2
xianyu search "显卡" --page 3
xianyu search "显卡" --page 3 --pages 2
```

`--page` is the starting page. `--pages` is the number of consecutive pages to fetch from that starting page.

Structured output:

```bash
xianyu search "显卡" --format json
xianyu search "显卡" --format ndjson
xianyu search "显卡" --format csv --output result.csv
```

Raw API JSON:

```bash
xianyu search "显卡" --json
xianyu search "显卡" --json --output raw.json
```

## Common Options

- `--page` — starting page, defaults to `1`
- `--pages` — consecutive pages to fetch per keyword from the starting page
- `--sort` — `default` or `latest`
- `--format` — `table`, `json`, `ndjson`, `csv`
- `--json` — output raw captured API payloads
- `--output` — write results to a file
- `--max-items` — limit returned normalized items
- `--storage-state` — specify a custom login-state file
- `--headful` — run search with a visible browser
- `--min-wait-ms` — wait between page actions
- `--navigation-timeout-ms` — Playwright timeout
- `--no-dedupe` — disable deduplication
- `--compact` — disable pretty JSON formatting
- `--dry-run` — validate arguments without a live request

## Output Fields

Normalized item output currently includes:

- `keyword`
- `title`
- `price`
- `area`
- `seller`
- `link`
- `image_url`
- `publish_time`
- `item_id`

## Notes

- Avoid large page counts.
- Avoid frequent live testing.
- Prefer `xianyu login` before live runs.
- Use `--dry-run` while adjusting parameters.
- For live verification, start with one keyword and one page.
