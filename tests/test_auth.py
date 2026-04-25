from __future__ import annotations

from xianyu_cli.auth import _extract_qr_code_content, _extract_qr_status, has_login_markers


def test_has_login_markers_accepts_auth_cookie_name() -> None:
    cookies = [
        {"name": "unb", "value": "x", "domain": ".goofish.com"},
    ]
    assert has_login_markers(cookies) is True


def test_has_login_markers_accepts_multiple_goofish_cookies() -> None:
    cookies = [
        {"name": "a", "value": "1", "domain": ".goofish.com"},
        {"name": "b", "value": "2", "domain": ".goofish.com"},
        {"name": "c", "value": "3", "domain": ".goofish.com"},
    ]
    assert has_login_markers(cookies) is False


def test_has_login_markers_rejects_non_goofish_cookies() -> None:
    cookies = [
        {"name": "unb", "value": "x", "domain": ".example.com"},
        {"name": "a", "value": "1", "domain": ".example.com"},
    ]
    assert has_login_markers(cookies) is False


def test_extract_qr_code_content_reads_generate_payload() -> None:
    payload = {
        "content": {
            "data": {
                "codeContent": "https://passport.goofish.com/qrcodeCheck.htm?lgToken=abc",
            }
        }
    }
    assert _extract_qr_code_content(payload) == "https://passport.goofish.com/qrcodeCheck.htm?lgToken=abc"


def test_extract_qr_status_reads_query_payload() -> None:
    payload = {
        "content": {
            "data": {
                "qrCodeStatus": "SCANED",
            }
        }
    }
    assert _extract_qr_status(payload) == "SCANED"
