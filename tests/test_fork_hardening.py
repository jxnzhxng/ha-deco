"""Tests for the changes this fork makes on top of upstream."""

from unittest.mock import MagicMock

from custom_components.tplink_deco.const import DOMAIN
from custom_components.tplink_deco.const import SERVICE_DOWNLOAD_SYSTEM_LOG
from custom_components.tplink_deco.const import SERVICE_RENAME_CLIENT
from custom_components.tplink_deco.const import SERVICE_SET_CLIENT_BLOCKED
from custom_components.tplink_deco.services import async_setup_services


def test_block_and_rename_actions_are_not_registered():
    hass = MagicMock()
    async_setup_services(hass)
    registered = {
        call.args[1]
        for call in hass.services.async_register.call_args_list
        if call.args[0] == DOMAIN
    }
    assert registered == {SERVICE_DOWNLOAD_SYSTEM_LOG}
    assert SERVICE_SET_CLIENT_BLOCKED not in registered
    assert SERVICE_RENAME_CLIENT not in registered


def test_options_do_not_offer_block_or_rename_controls():
    from custom_components.tplink_deco.config_flow import _get_schema

    schema = _get_schema({})
    keys = {str(key) for key in getattr(schema, "schema", schema)}
    assert keys
    assert not any("experimental" in key for key in keys)
