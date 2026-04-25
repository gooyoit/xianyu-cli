# xianyu-cli

[English](./README.md) | 中文

一个面向闲鱼（Goofish）的命令行工具：基于 Playwright 搜索商品，并支持输出抓到的原始搜索接口响应。

## 声明

本项目仅出于个人兴趣、学习交流与技术研究目的而创建和分享。

- 严禁将本项目用于任何商业用途、获利行为、大规模抓取或其他违法违规场景。
- 任何人使用本项目所产生的风险均由使用者自行承担。
- 因使用或滥用本项目而导致的任何直接或间接后果，包括但不限于数据风险、账号限制、法律责任或其他损失，均由使用者本人承担。
- 本项目作者及贡献者不对因使用本项目所引发的任何责任、损失或风险承担任何义务。
- 欢迎技术爱好者在合法合规前提下共同学习、研究和交流。

## 功能特性

- 🔐 **登录**：浏览器辅助登录、保存登录态、查看登录状态、退出登录
- 🔍 **搜索**：支持单关键词、多关键词、关键词文件输入
- 📦 **多种输出格式**：`table`、`json`、`ndjson`、`csv`
- 🧾 **原始接口输出**：`--json` 可直接返回抓到的搜索接口原始响应
- ♻️ **登录态复用**：如果本地已保存 Playwright 登录态，后续搜索自动复用
- 🧹 **纯 CLI 设计**：不用 FastAPI，不用数据库

## 安装

```bash
# 发布到 PyPI 后推荐这样安装
pip install xianyu-cli
playwright install chromium
```

从源码安装：

```bash
git clone <你的仓库地址>
cd xianyu-cli
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m playwright install chromium
```

## 用法

```bash
# ─── 登录 ─────────────────────────────────────────
xianyu login                               # 打开浏览器并保存登录态
xianyu login --qrcode                      # 在终端输出二维码并自动完成登录流程
xianyu login --auto-detect                 # 检测到强认证 Cookie 后自动保存
xianyu status                              # 查看当前保存的登录状态
xianyu logout                              # 删除已保存的登录态
xianyu login --storage-state ./state.json  # 保存到自定义路径

# ─── 搜索 ─────────────────────────────────────────
xianyu search "iPhone 15"                  # 基础搜索
xianyu search "显卡" --pages 2             # 分页
xianyu search --keyword 显卡 --keyword 相机
xianyu search --keyword-file keywords.txt

# 结构化输出
xianyu search "显卡" --format json
xianyu search "显卡" --format ndjson
xianyu search "显卡" --format csv --output result.csv

# 原始搜索接口响应
xianyu search "显卡" --json
xianyu search "显卡" --json --output raw.json

# 只校验参数，不发真实请求
xianyu search "MacBook" --dry-run --format json
```

## 登录说明

闲鱼在匿名状态下，经常返回空结果或不完整结果。实际使用时，通常建议先登录。

`xianyu login` 会打开一个可见的 Chromium 窗口。你在浏览器里完成闲鱼登录后，回到终端按一次回车保存。

如果你更想用终端二维码登录，可以执行：

```bash
xianyu login --qrcode
```

这个模式会在后台维持一个 Playwright 浏览器上下文，在终端直接渲染二维码，轮询扫码状态，并在你确认登录后自动保存登录态。

CLI 现在支持三种登录方式：

- 手工确认：默认且更推荐，登录完成后回终端按回车保存
- 自动探测：可选，用 `xianyu login --auto-detect`
- 终端二维码登录：用 `xianyu login --qrcode`

默认登录态保存路径：

```bash
~/.config/xianyu-cli/storage-state.json
```

保存后，后续执行 `xianyu search ...` 时会自动复用这份登录态。

如果你之前遇到“浏览器刚打开就自动关闭”，原因是旧版本把匿名 Cookie 误判成已登录。现在默认改成手工确认保存，会更稳。

## 搜索说明

基础搜索：

```bash
xianyu search "iPhone 15"
```

多关键词：

```bash
xianyu search "显卡" "机械键盘" "相机"
xianyu search --keyword 显卡 --keyword 机械键盘 --keyword 相机
xianyu search --keyword-file keywords.txt
```

结构化输出：

```bash
xianyu search "显卡" --format json
xianyu search "显卡" --format ndjson
xianyu search "显卡" --format csv --output result.csv
```

原始接口 JSON：

```bash
xianyu search "显卡" --json
xianyu search "显卡" --json --output raw.json
```

## 常用参数

- `--pages`：每个关键词抓取页数
- `--sort`：`default` 或 `latest`
- `--format`：`table`、`json`、`ndjson`、`csv`
- `--json`：输出抓到的原始接口响应
- `--output`：写入文件
- `--max-items`：限制整理后结果条数
- `--storage-state`：指定自定义登录态文件
- `--headful`：用可见浏览器执行搜索
- `--min-wait-ms`：页面动作之间的等待时间
- `--navigation-timeout-ms`：Playwright 超时时间
- `--no-dedupe`：关闭去重
- `--compact`：关闭 JSON 美化输出
- `--dry-run`：只校验参数，不发真实请求

## 输出字段

整理后的商品结果目前包含：

- `keyword`
- `title`
- `price`
- `area`
- `seller`
- `link`
- `image_url`
- `publish_time`
- `item_id`

## 使用建议

- 不要一次抓太多页。
- 不要频繁做真实请求测试。
- 建议正式抓取前先执行 `xianyu login`。
- 调参数时优先用 `--dry-run`。
- 真实验证时先从单关键词、单页开始。
