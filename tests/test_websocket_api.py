"""Tests for the mcp moel_context_protocol websocket API."""

import pytest
import json
from decimal import Decimal
from typing import Any

from syrupy import SnapshotAssertion

from homeassistant.components.homeassistant.exposed_entities import async_expose_entity
from homeassistant.const import SERVICE_TURN_ON
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.helpers import device_registry as dr, entity_registry as er


from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_service,
)
from pytest_homeassistant_custom_component.typing import WebSocketGenerator


@pytest.fixture(autouse=True, name="setup_integration")
async def mock_setup_integration(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Setup the integration"""
    assert await async_setup_component(hass, "homeassistant", {})
    assert await async_setup_component(hass, "conversation", {})


@pytest.fixture(autouse=True)
def mock_light_entity_fixture(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    setup_integration: Any,
) -> None:
    """Fixture for light entity."""
    entry1 = entity_registry.async_get_or_create(
        "light",
        "kitchen",
        "mock-id-kitchen",
        original_name="Kitchen",
        suggested_object_id="kitchen",
    )
    hass.states.async_set(
        entry1.entity_id,
        "on",
        {"friendly_name": "Kitchen", "temperature": Decimal("0.9"), "humidity": 65},
    )
    async_expose_entity(hass, "assistant", "light.kitchen", True)


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
    results = msg["result"]["tools"]

    # Pick a single arbitrary tool to test
    tool = next(iter(tool for tool in results if tool["name"] == "HassTurnOn"))
    assert tool.get("name") == snapshot
    assert tool.get("description") == snapshot
    assert tool.get("input_schema", {}).get("properties", {}).get("name") == snapshot


async def test_tools_call(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the tools call command."""
    calls = async_mock_service(hass, "light", SERVICE_TURN_ON)

    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {
            "type": "mcp/tools/call",
            "name": "HassTurnOn",
            "arguments": {"name": "kitchen"},
        }
    )
    msg = await client.receive_json()
    assert msg["success"]
    results = msg["result"]["content"]
    assert len(results) == 1
    result = results[0]
    data = result["text"]
    response = json.loads(data)
    assert response["data"] == snapshot

    assert len(calls) == 1
    call = calls[0]
    assert call.domain == "light"
    assert call.service == "turn_on"
    assert call.data == {"entity_id": ["light.kitchen"]}


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
            "arguments": {"name": "unknown entity name"},
        }
    )
    msg = await client.receive_json()
    assert msg["success"]
    results = msg["result"]["content"]
    assert len(results) == 1
    result = results[0]
    data = result["text"]
    error = json.loads(data)
    assert error.get("error") == "MatchFailedError"


async def test_prompts_list(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the tools list command."""

    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {
            "type": "mcp/prompts/list",
        }
    )
    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"][0]["name"] == "assist"


async def test_prompts_get(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the tools list command."""

    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {
            "type": "mcp/prompts/get",
            "name": "assist",
        }
    )
    msg = await client.receive_json()
    assert msg["success"]
    prompt = msg["result"]["messages"][0]["content"]["text"]
    assert "Answer questions about the world" in prompt
