"""Tests for session token redaction in the integration's log output."""

import logging

from custom_components.tplink_deco.log_redaction import SessionTokenFilter
from custom_components.tplink_deco.log_redaction import redact

URL = "https://192.168.68.1/cgi-bin/luci/;stok=0123abcd/admin/client?form=client_list"


def test_redact_removes_stok_and_keeps_the_rest():
    assert redact(f"403, message='Forbidden', url='{URL}'") == (
        "403, message='Forbidden', url='https://192.168.68.1/cgi-bin/luci/"
        ";stok=REDACTED/admin/client?form=client_list'"
    )


def test_redact_removes_legacy_session_id():
    assert redact("url=http://10.0.0.1/admin/device?form=device_list&id=deadbeef") == (
        "url=http://10.0.0.1/admin/device?form=device_list&id=REDACTED"
    )


def test_redact_keeps_the_empty_login_token():
    text = "http://10.0.0.1/cgi-bin/luci/;stok=/login?form=keys"
    assert redact(text) == text


def test_every_integration_logger_has_the_filter():
    import custom_components.tplink_deco  # noqa: F401

    for module in ("", ".api", ".coordinator", ".services"):
        logger = logging.getLogger(f"custom_components.tplink_deco{module}")
        assert any(isinstance(f, SessionTokenFilter) for f in logger.filters)


def test_filter_redacts_message_args_and_traceback(caplog):
    logger = logging.getLogger("custom_components.tplink_deco.api")
    with caplog.at_level(logging.DEBUG, logger=logger.name):
        try:
            raise ValueError(URL)
        except ValueError as err:
            logger.error("List clients client error: %s", err, exc_info=True)
    assert "0123abcd" not in caplog.text
    record = caplog.records[-1]
    assert "0123abcd" not in record.getMessage()
    assert "0123abcd" not in record.exc_text
    assert "stok=REDACTED" in record.getMessage()
