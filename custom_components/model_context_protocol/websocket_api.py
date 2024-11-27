"""Model Context Protocol websocket API."""

from collections.abc import Callable
from typing import Any
from dataclasses import dataclass

import voluptuous as vol
from voluptuous_openapi import convert

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import llm

from .const import DEFAULT_LLM_API, DOMAIN


@callback
def async_register_websocket_api(hass: HomeAssistant) -> None:
    """Register the websocket API."""
    websocket_api.async_register_command(hass, websocket_list_tools)
    websocket_api.async_register_command(hass, websocket_call_tool)


@dataclass
class InputSchema:
    """A JSON Schema for a tool's input parameters."""

    type: str
    properties: dict[str, Any]


@dataclass
class Tool:
    """A tool that can be called via the Model Context Protocol."""

    name: str
    description: str
    input_schema: dict[str, Any]


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


@websocket_api.websocket_command(
    {
        vol.Required("type"): "mcp/tools/list",
    }
)
@websocket_api.decorators.async_response
async def websocket_list_tools(
    hass: HomeAssistant,
    connection: websocket_api.connection.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle listing tools."""

    llm_context = llm.LLMContext(
        platform=DOMAIN,
        context=connection.context(msg),
        user_prompt=None,
        language=None,
        assistant=None,
        device_id=None,
    )
    llm_api = await llm.async_get_api(
        hass,
        DEFAULT_LLM_API,
        llm_context,
    )
    tools = [_format_tool(tool, llm_api.custom_serializer) for tool in llm_api.tools]
    connection.send_result(msg["id"], tools)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "mcp/tools/call",
    }
)
@websocket_api.decorators.async_response
async def websocket_call_tool(
    hass: HomeAssistant,
    connection: websocket_api.connection.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle calling tools."""
    connection.send_result(msg["id"], [])
