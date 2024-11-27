"""Tests for the mcp moel_context_protocol websocket API."""


import asyncio
import base64
from typing import Any
from unittest.mock import ANY, patch

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr

from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import WebSocketGenerator


@pytest.fixture(autouse=True)
def mock_setup_integration(config_entry: MockConfigEntry) -> None:
    """Setup the integration"""


async def test_list_tools(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Test the list_tools command."""
    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {
            "type": "mcp/tools/list",
        }
    )
    msg = await client.receive_json()
    assert msg["success"]
    assert msg.get("result") == []



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
