"""Tests for the experimental single-client block list action."""

import base64
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest
import voluptuous as vol

from custom_components.tplink_deco.api import TplinkDecoApi
from custom_components.tplink_deco.exceptions import TimeoutException
from custom_components.tplink_deco.exceptions import UnexpectedApiException
from custom_components.tplink_deco.services import SET_CLIENT_BLOCKED_SCHEMA

MAC = "02:00:00:00:00:01"
EMPTY_LIST = {"result": {"client_list": {}}}
BLOCKED_LIST = {"result": {"client_list": [{"mac": "02-00-00-00-00-01"}]}}


@pytest.fixture
def api():
    api = TplinkDecoApi(
        MagicMock(), "http://192.0.2.1", "admin", "test", verify_ssl=False
    )
    api.async_login_if_needed = AsyncMock()
    api._encode_payload = MagicMock(side_effect=lambda payload: payload)
    api._decrypt_data = MagicMock(side_effect=lambda _context, data: data)
    api._async_post = AsyncMock()
    return api


@pytest.mark.asyncio
@pytest.mark.parametrize("blocked", [True, False])
async def test_change_checks_blocklist_before_and_after_write(api, blocked):
    before, after = (
        (EMPTY_LIST, BLOCKED_LIST) if blocked else (BLOCKED_LIST, EMPTY_LIST)
    )
    api._async_post.side_effect = [{"data": before}, {"error_code": 0}, {"data": after}]

    assert await api.async_set_client_blocked(MAC, blocked, "Test client")
    requests = [call.kwargs for call in api._async_post.await_args_list]
    assert all(call["params"] == {"form": "black_list"} for call in requests)
    assert [call["data"]["operation"] for call in requests] == [
        "list",
        "block" if blocked else "unblock",
        "list",
    ]
    assert requests[1]["data"]["params"]["client_list"] == (
        [
            {
                "mac": "02-00-00-00-00-01",
                "name": base64.b64encode(b"Test client").decode(),
                "client_type": "other",
            }
        ]
        if blocked
        else ["02-00-00-00-00-01"]
    )


@pytest.mark.asyncio
async def test_unsupported_list_shape_does_not_trigger_a_write(api):
    api._async_post.return_value = {"error_code": 0}
    with pytest.raises(UnexpectedApiException, match="invalid blocked client list"):
        await api.async_set_client_blocked(MAC, True)
    api._async_post.assert_awaited_once()


@pytest.mark.asyncio
async def test_already_blocked_is_not_written_again(api):
    api._async_post.return_value = {"data": BLOCKED_LIST}
    assert not await api.async_set_client_blocked(MAC, True)
    api._async_post.assert_awaited_once()


@pytest.mark.asyncio
async def test_timeout_does_not_repeat_the_write(api):
    api._async_post.side_effect = [{"data": EMPTY_LIST}, TimeoutException()]
    with pytest.raises(TimeoutException):
        await api.async_set_client_blocked(MAC, True)
    assert api._async_post.await_count == 2


@pytest.mark.asyncio
async def test_success_response_without_list_change_is_not_success(api):
    api._async_post.side_effect = [
        {"data": EMPTY_LIST},
        {"error_code": 0},
        {"data": EMPTY_LIST},
    ]
    with pytest.raises(UnexpectedApiException, match="did not confirm"):
        await api.async_set_client_blocked(MAC, True)


@pytest.mark.parametrize("mac", ["", "ff:ff:ff:ff:ff:ff", "00:00:00:00:00:00"])
def test_invalid_target_is_rejected(mac):
    with pytest.raises(vol.Invalid):
        SET_CLIENT_BLOCKED_SCHEMA({"mac": mac, "blocked": True})
