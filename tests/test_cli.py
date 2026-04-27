from __future__ import annotations

import json
from argparse import Namespace

import pytest

from xianyu_cli.cli import main, parse_options
from xianyu_cli.models import SearchRunResult


def test_parse_options_supports_multiple_keyword_sources(tmp_path) -> None:
    keyword_file = tmp_path / "keywords.txt"
    keyword_file.write_text("相机\n耳机\n", encoding="utf-8")

    args = Namespace(
        keywords=["手机"],
        keyword=["平板"],
        keyword_file=str(keyword_file),
        pages=2,
        sort="latest",
        headful=False,
        output_format="json",
        output=None,
        storage_state=None,
        min_wait_ms=800,
        navigation_timeout_ms=10_000,
        max_items=None,
        no_dedupe=False,
        compact=False,
        dry_run=False,
        json=False,
    )

    options = parse_options(args)
    assert options.keywords == ["手机", "平板", "相机", "耳机"]


def test_main_dry_run_prints_options(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["search", "显卡", "--dry-run", "--format", "json"])
    assert code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["keywords"] == ["显卡"]
    assert output["output_format"] == "json"


def test_main_json_prints_raw_payloads(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def fake_scrape_all(_options):
        return [
            SearchRunResult(
                keyword="显卡",
                items=[],
                raw_payloads=[{"data": {"resultList": [{"id": "1"}]}}],
            )
        ]

    monkeypatch.setattr("xianyu_cli.cli.scrape_all", fake_scrape_all)
    code = main(["search", "显卡", "--json"])
    assert code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["keywords"] == ["显卡"]
    assert output["responses"][0]["payloads"][0]["data"]["resultList"][0]["id"] == "1"


def test_login_qrcode_uses_terminal_qr_flow(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def fake_login_with_terminal_qrcode(_path, *, timeout_seconds):
        assert timeout_seconds == 300
        from xianyu_cli.auth import AuthState

        return AuthState(
            state_path="/tmp/state.json",
            exists=True,
            logged_in=True,
            cookie_count=10,
            goofish_cookie_count=10,
        )

    monkeypatch.setattr(
        "xianyu_cli.cli.login_with_terminal_qrcode",
        fake_login_with_terminal_qrcode,
    )
    code = main(["login", "--qrcode"])
    assert code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["logged_in"] is True


def test_main_propagates_login_required_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_scrape_all(_options):
        raise RuntimeError("闲鱼搜索接口要求登录校验")

    monkeypatch.setattr("xianyu_cli.cli.scrape_all", fake_scrape_all)
    with pytest.raises(RuntimeError, match="登录校验"):
        main(["search", "显卡"])


def test_parse_options_uses_default_storage_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    state_file = tmp_path / "storage-state.json"
    state_file.write_text('{"cookies":[]}', encoding="utf-8")
    monkeypatch.setattr("xianyu_cli.cli.get_default_storage_state_path", lambda: state_file)

    args = Namespace(
        keywords=["手机"],
        keyword=[],
        keyword_file=None,
        pages=1,
        sort="latest",
        headful=False,
        output_format="json",
        output=None,
        storage_state=None,
        min_wait_ms=800,
        navigation_timeout_ms=10_000,
        max_items=None,
        no_dedupe=False,
        compact=False,
        dry_run=False,
        json=False,
    )

    options = parse_options(args)
    assert options.storage_state == str(state_file)
    assert options.storage_state_explicit is False


def test_status_outputs_saved_state_summary(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    state_file = tmp_path / "state.json"
    state_file.write_text(
        json.dumps(
            {
                "cookies": [
                    {"name": "unb", "value": "1", "domain": ".goofish.com"},
                    {"name": "other", "value": "2", "domain": ".example.com"},
                ]
            }
        ),
        encoding="utf-8",
    )

    code = main(["status", "--storage-state", str(state_file)])
    assert code == 0
    output = capsys.readouterr().out
    assert "ok: true" in output
    assert "schema_version: '1'" in output
    assert "  logged_in: true" in output
    assert "  goofish_cookie_count: 1" in output


def test_status_outputs_not_logged_in_for_non_auth_cookie(
    tmp_path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_file = tmp_path / "state.json"
    state_file.write_text(
        json.dumps(
            {
                "cookies": [
                    {"name": "foo", "value": "1", "domain": ".goofish.com"},
                ]
            }
        ),
        encoding="utf-8",
    )

    code = main(["status", "--storage-state", str(state_file)])
    assert code == 1
    output = capsys.readouterr().out
    assert "ok: false" in output
    assert "  logged_in: false" in output
    assert "  code: not_authenticated" in output
    assert "please re-login with: xianyu login" in output


def test_status_outputs_not_logged_in_for_missing_state(
    tmp_path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    state_file = tmp_path / "missing.json"

    code = main(["status", "--storage-state", str(state_file)])
    assert code == 1
    output = capsys.readouterr().out
    assert "ok: false" in output
    assert f"  state_path: '{state_file}'" in output
    assert "  exists: false" in output
    assert "  code: not_authenticated" in output
