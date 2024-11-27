"""Tests for the model_context_protocol component."""

import pytest

from homeassistant.config_entries import ConfigEntryState

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
)


@pytest.fixture(autouse=True)
def mock_setup_integration(config_entry: MockConfigEntry) -> None:
    """Setup the integration"""


async def test_init(config_entry: MockConfigEntry) -> None:
    """Test the integration is initialized."""
    assert config_entry.state is ConfigEntryState.LOADED
