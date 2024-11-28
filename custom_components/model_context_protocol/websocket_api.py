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
from homeassistant.helpers import (
    llm,
    template,
)

from .const import DEFAULT_LLM_API, DOMAIN
from .model import Tool, InputSchema, TextContent


_LOGGER = logging.getLogger(__name__)

URI_PREFIX = "file:///"
ASSISTANT = "assistant"


@callback
def async_register_websocket_api(hass: HomeAssistant) -> None:
    """Register the websocket API."""
    websocket_api.async_register_command(hass, websocket_tools_list)
    websocket_api.async_register_command(hass, websocket_tools_call)
    websocket_api.async_register_command(hass, websocket_prompts_list)
    websocket_api.async_register_command(hass, websocket_prompts_get)


def _entity_id_to_uri(entity_id: str) -> str:
    """Create an entity ID URI."""
    entity_id_path = "/".join(entity_id.split("."))
    return f"{URI_PREFIX}{entity_id_path}"


def _entity_id_from_uri(uri: str) -> str:
    """Create an entity ID URI."""
    if not uri.startswith(URI_PREFIX):
        raise vol.Invalid(f"Invalid URI format did not start with {URI_PREFIX}")
    entity_id_path = uri[len(URI_PREFIX) :]
    return ".".join(entity_id_path.split("/"))


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
        assistant=ASSISTANT,
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


@websocket_api.websocket_command(
    {
        vol.Required("type"): "mcp/prompts/list",
    }
)
@websocket_api.decorators.async_response
async def websocket_prompts_list(
    hass: HomeAssistant,
    connection: websocket_api.connection.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle listing tools."""
    _LOGGER.debug("List prompts: %s", msg)
    connection.send_result(
        msg["id"],
        [
            {
                "name": "assist",
                "description": "Prompt for the Home Assistant Assist actions that contains the current state of all entities in the Home.",
            }
        ],
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "mcp/prompts/get",
        vol.Required("name"): str,
    }
)
@websocket_api.decorators.async_response
async def websocket_prompts_get(
    hass: HomeAssistant,
    connection: websocket_api.connection.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle listing tools."""
    if msg["name"] != "assist":
        raise vol.Invalid("Invalid prompt name")
    llm_context = _llm_context(connection, msg)
    llm_api = await llm.async_get_api(hass, DEFAULT_LLM_API, llm_context)

    _LOGGER.debug("List prompts: %s", msg)
    if (
        llm_context.context
        and llm_context.context.user_id
        and (user := await hass.auth.async_get_user(llm_context.context.user_id))
    ):
        user_name = user.name
    prompt = "\n".join(
        [
            template.Template(
                llm.BASE_PROMPT + llm.DEFAULT_INSTRUCTIONS_PROMPT,
                hass,
            ).async_render(
                {
                    "ha_name": hass.config.location_name,
                    "user_name": user_name,
                    "llm_context": llm_context,
                },
                parse_result=False,
            ),
            llm_api.api_prompt,
        ]
    )
    connection.send_result(
        msg["id"],
        {
            "description": "Prompt for the Home Assistant Assist actions that contains the current state of all entities in the Home.",
            "messages": [
                {
                    "role": "assistant",
                    "content": {
                        "type": "text",
                        "text": prompt,
                    },
                }
            ],
        },
    )
