"""Model Context Protocol websocket API."""

import asyncio
import base64
from collections.abc import AsyncGenerator, Callable
import contextlib
import logging
import math
from typing import Any, Final

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.const import ATTR_DEVICE_ID, ATTR_SECONDS, MATCH_ALL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.util import language as language_util


@callback
def async_register_websocket_api(hass: HomeAssistant) -> None:
    """Register the websocket API."""
    websocket_api.async_register_command(hass, websocket_list_tools)
    websocket_api.async_register_command(hass, websocket_call_tool)


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
    connection.send_result(msg["id"], [])


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
