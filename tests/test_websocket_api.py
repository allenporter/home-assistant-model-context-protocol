"""Tests for the mcp moel_context_protocol websocket API."""

import pytest

from syrupy import SnapshotAssertion

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import WebSocketGenerator


@pytest.fixture(autouse=True)
def mock_setup_integration(config_entry: MockConfigEntry) -> None:
    """Setup the integration"""


async def test_list_tools(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the list_tools command."""
    assert await async_setup_component(hass, "homeassistant", {})
    assert await async_setup_component(hass, "conversation", {})

    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {
            "type": "mcp/tools/list",
        }
    )
    msg = await client.receive_json()
    assert msg["success"]
    results = msg.get("result")

    # Pick a single arbitrary tool to test
    tool = next(iter(tool for tool in results if tool["name"] == "HassTurnOn"))
    assert tool == snapshot



async def test_call_tool(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Test the call_tool command."""
    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {
            "type": "mcp/tools/call",
        }
    )
    msg = await client.receive_json()
    assert msg["success"]
    assert msg.get("result") == []
