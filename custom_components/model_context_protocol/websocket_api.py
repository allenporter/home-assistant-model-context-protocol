"""Model Context Protocol websocket API."""

import dataclasses
from collections.abc import Callable
from typing import Any, cast
import logging
import json
from enum import Enum
from decimal import Decimal


import voluptuous as vol
from voluptuous_openapi import convert

from homeassistant.components.homeassistant import async_should_expose
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.components.script import DOMAIN as SCRIPT_DOMAIN
from homeassistant.helpers import (
    llm,
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
)

from .const import DEFAULT_LLM_API, DOMAIN
from .model import Tool, InputSchema, TextContent, Resource, TextResourceContents


_LOGGER = logging.getLogger(__name__)

URI_PREFIX = "entity_id://"


@callback
def async_register_websocket_api(hass: HomeAssistant) -> None:
    """Register the websocket API."""
    websocket_api.async_register_command(hass, websocket_tools_list)
    websocket_api.async_register_command(hass, websocket_tools_call)
    websocket_api.async_register_command(hass, websocket_resources_list)
    websocket_api.async_register_command(hass, websocket_resources_read)


def _format_tool(
    tool: llm.Tool, custom_serializer: Callable[[Any], Any] | None
) -> Tool:
    """Format tool specification."""
    input_schema = convert(tool.parameters, custom_serializer=custom_serializer)
    return Tool(
        name=tool.name,
        description=tool.description or "",
        input_schema=InputSchema(
            type="object",
            properties=input_schema["properties"],
        ),
    )


def _llm_context(
    connection: websocket_api.connection.ActiveConnection,
    msg: dict[str, Any],
) -> llm.LLMContext:
    return llm.LLMContext(
        platform=DOMAIN,
        context=connection.context(msg),
        user_prompt=None,
        language="*",
        assistant=DOMAIN,
        device_id=None,
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "mcp/tools/list",
    }
)
@websocket_api.decorators.async_response
async def websocket_tools_list(
    hass: HomeAssistant,
    connection: websocket_api.connection.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle listing tools."""
    _LOGGER.debug("List tools: %s", msg)
    llm_context = _llm_context(connection, msg)
    llm_api = await llm.async_get_api(hass, DEFAULT_LLM_API, llm_context)
    tools = [_format_tool(tool, llm_api.custom_serializer) for tool in llm_api.tools]
    connection.send_result(msg["id"], {"tools": tools})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "mcp/tools/call",
        vol.Required("name"): str,
        vol.Optional("arguments"): dict,
    }
)
@websocket_api.decorators.async_response
async def websocket_tools_call(
    hass: HomeAssistant,
    connection: websocket_api.connection.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle calling tools."""
    llm_context = _llm_context(connection, msg)
    llm_api = await llm.async_get_api(hass, DEFAULT_LLM_API, llm_context)

    tool_input = llm.ToolInput(
        tool_name=cast(str, msg.get("name")),
        tool_args=msg.get("arguments", {}),
    )
    _LOGGER.debug("Tool call: %s(%s)", tool_input.tool_name, tool_input.tool_args)

    is_error = False
    try:
        tool_response = await llm_api.async_call_tool(tool_input)
    except (HomeAssistantError, vol.Invalid) as e:
        is_error = True
        tool_response = {"error": type(e).__name__}
        if str(e):
            tool_response["error_text"] = str(e)

    _LOGGER.debug("Tool response: %s", tool_response)
    connection.send_result(
        msg["id"],
        {
            "content": [
                TextContent(
                    type="text",
                    text=json.dumps(tool_response),
                )
            ],
            "is_error": is_error,
        },
    )


def _get_exposed_entities(
    hass: HomeAssistant, assistant: str
) -> dict[str, dict[str, Any]]:
    """Get exposed entities."""
    area_registry = ar.async_get(hass)
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    interesting_attributes = {
        "temperature",
        "current_temperature",
        "temperature_unit",
        "brightness",
        "humidity",
        "unit_of_measurement",
        "device_class",
        "current_position",
        "percentage",
        "volume_level",
        "media_title",
        "media_artist",
        "media_album_name",
    }

    entities = {}

    for state in hass.states.async_all():
        _LOGGER.debug("s=%s", state)
        if (
            not async_should_expose(hass, assistant, state.entity_id)
            or state.domain == SCRIPT_DOMAIN
        ):
            continue
        _LOGGER.debug("pass=%s", state)

        description: str | None = None
        entity_entry = entity_registry.async_get(state.entity_id)
        names = [state.name]
        area_names = []

        if entity_entry is not None:
            names.extend(entity_entry.aliases)
            if entity_entry.area_id and (
                area := area_registry.async_get_area(entity_entry.area_id)
            ):
                # Entity is in area
                area_names.append(area.name)
                area_names.extend(area.aliases)
            elif entity_entry.device_id and (
                device := device_registry.async_get(entity_entry.device_id)
            ):
                # Check device area
                if device.area_id and (
                    area := area_registry.async_get_area(device.area_id)
                ):
                    area_names.append(area.name)
                    area_names.extend(area.aliases)

        info: dict[str, Any] = {
            "names": ", ".join(names),
            "domain": state.domain,
            "state": state.state,
        }

        if description:
            info["description"] = description

        if area_names:
            info["areas"] = ", ".join(area_names)

        if attributes := {
            attr_name: (
                str(attr_value)
                if isinstance(attr_value, (Enum, Decimal, int))
                else attr_value
            )
            for attr_name, attr_value in state.attributes.items()
            if attr_name in interesting_attributes
        }:
            info["attributes"] = attributes

        entities[state.entity_id] = info

    return entities


@websocket_api.websocket_command(
    {
        vol.Required("type"): "mcp/resources/list",
    }
)
@websocket_api.decorators.async_response
async def websocket_resources_list(
    hass: HomeAssistant,
    connection: websocket_api.connection.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle listing resources."""
    _LOGGER.debug("List resource: %s", msg)
    entities = _get_exposed_entities(hass, "assistant")
    resources = [
        Resource(
            uri=f"{URI_PREFIX}{entity_id}",
            name=info["names"],
            description=info.get("description", ""),
            mimeType=None,
        )
        for entity_id, info in entities.items()
    ]
    _LOGGER.debug("Sent: %s", len(resources))
    connection.send_result(
        msg["id"],
        {
            "resources": resources,
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "mcp/resources/read",
        vol.Required("uri"): str,
    }
)
@websocket_api.decorators.async_response
async def websocket_resources_read(
    hass: HomeAssistant,
    connection: websocket_api.connection.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle listing resources."""
    _LOGGER.debug("Read resource: %s", msg)
    uri = msg["uri"]
    if not uri.startswith(URI_PREFIX):
        raise vol.Invalid(f"Invalid URI format did not start with {URI_PREFIX}")
    entity_id = uri[len(URI_PREFIX) :]
    entities = _get_exposed_entities(hass, "assistant")
    if entity_id not in entities:
        raise vol.Invalid(f"Entity {entity_id} not found")
    info = entities[entity_id]
    connection.send_result(
        msg["id"],
        {
            "contents": [
                dataclasses.asdict(TextResourceContents(uri=uri, text=json.dumps(info))),
            ]
        },
    )
