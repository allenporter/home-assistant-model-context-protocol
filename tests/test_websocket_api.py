"""Tests for the mcp moel_context_protocol websocket API."""

import pytest
import json

from syrupy import SnapshotAssertion

from homeassistant.const import SERVICE_TURN_ON
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.helpers import device_registry as dr, entity_registry as er

from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service
from pytest_homeassistant_custom_component.typing import WebSocketGenerator


@pytest.fixture(autouse=True)
async def mock_setup_integration(
    hass: HomeAssistant, config_entry: MockConfigEntry,
) -> None:
    """Setup the integration"""
    assert await async_setup_component(hass, "homeassistant", {})
    assert await async_setup_component(hass, "conversation", {})


async def test_tools_list(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the tools list command."""

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
    assert tool.get("name") == snapshot
    assert tool.get("description") == snapshot
    assert tool.get("input_schema", {}).get("properties", {}).get("name") == snapshot


async def test_tools_call(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    config_entry: MockConfigEntry,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the tools call command."""
    hass.states.async_set("light.test_light", "off")
    calls = async_mock_service(hass, "light", SERVICE_TURN_ON)

    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {
            "type": "mcp/tools/call",
            "name": "HassTurnOn",
            "arguments": {"name": "test light"},
        }
    )
    msg = await client.receive_json()
    assert msg["success"]
    results = msg.get("result")
    assert len(results) == 1
    result = results[0]
    data = result["text"]
    response = json.loads(data)
    assert response["data"] == snapshot

    assert len(calls) == 1
    call = calls[0]
    assert call.domain == "light"
    assert call.service == "turn_on"
    assert call.data == {"entity_id": ["light.test_light"]}


async def test_tools_call_error(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Test the tools call command that fails with an exception."""
    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {
            "type": "mcp/tools/call",
            "name": "HassTurnOn",
            "arguments": {"name": "light.kitchen"},
        }
    )
    msg = await client.receive_json()
    assert msg["success"]
    results = msg.get("result")
    assert len(results) == 1
    result = results[0]
    data = result["text"]
    error = json.loads(data)
    assert error.get("error") == "MatchFailedError"
