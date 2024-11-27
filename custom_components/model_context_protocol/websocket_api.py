"""Model Context Protocol websocket API."""

from collections.abc import Callable
from typing import Any, cast
import logging
import json

import voluptuous as vol
from voluptuous_openapi import convert

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import llm

from .const import DEFAULT_LLM_API, DOMAIN
from .model import Tool, InputSchema, TextContent


_LOGGER = logging.getLogger(__name__)


@callback
def async_register_websocket_api(hass: HomeAssistant) -> None:
    """Register the websocket API."""
    websocket_api.async_register_command(hass, websocket_list_tools)
    websocket_api.async_register_command(hass, websocket_call_tool)


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
        language=None,
        assistant=None,
        device_id=None,
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
    llm_context = _llm_context(connection, msg)
    llm_api = await llm.async_get_api(hass, DEFAULT_LLM_API, llm_context)
    tools = [_format_tool(tool, llm_api.custom_serializer) for tool in llm_api.tools]
    connection.send_result(msg["id"], tools)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "mcp/tools/call",
        vol.Required("name"): str,
        vol.Optional("arguments"): dict,
    }
)
@websocket_api.decorators.async_response
async def websocket_call_tool(
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

    try:
        tool_response = await llm_api.async_call_tool(tool_input)
    except (HomeAssistantError, vol.Invalid) as e:
        tool_response = {"error": type(e).__name__}
        if str(e):
            tool_response["error_text"] = str(e)

    _LOGGER.debug("Tool response: %s", tool_response)
    connection.send_result(
        msg["id"],
        [
            TextContent(
                type="text",
                text=json.dumps(tool_response),
            )
        ],
    )
