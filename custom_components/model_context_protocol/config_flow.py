"""Config flow for model_context_protocol integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.helpers.schema_config_entry_flow import (
    SchemaConfigFlowHandler,
    SchemaFlowFormStep,
)

from .const import DOMAIN


CONFIG_FLOW = {"user": SchemaFlowFormStep(vol.Schema({}))}

OPTIONS_FLOW = {
    "init": SchemaFlowFormStep(),
}


class ModelContextProtocolConfigFlowHandler(SchemaConfigFlowHandler, domain=DOMAIN):
    """Handle a config flow for Switch as X."""

    config_flow = CONFIG_FLOW
    options_flow = OPTIONS_FLOW

    VERSION = 1
    MINOR_VERSION = 1

    def async_config_entry_title(self, options: Mapping[str, Any]) -> str:
        """Return config entry title."""
        return "Model Context Protocol"
