"""Fixtures for the custom component."""

from collections.abc import Generator, AsyncGenerator
import logging
from unittest.mock import patch

import pathlib
import pytest
from syrupy.extensions.amber import AmberSnapshotExtension
from syrupy.location import PyTestLocation
from syrupy import SnapshotAssertion

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
)

from custom_components.model_context_protocol.const import (
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


DIFFERENT_DIRECTORY = "snapshots"


class DifferentDirectoryExtension(AmberSnapshotExtension):
    """Extension to set a different snapshot directory."""

    @classmethod
    def dirname(cls, *, test_location: "PyTestLocation") -> str:
        """Override the snapshot directory name."""
        return str(
            pathlib.Path(test_location.filepath).parent.joinpath(DIFFERENT_DIRECTORY)
        )


@pytest.fixture
def snapshot(snapshot: SnapshotAssertion):
    """Fixture to override the snapshot directory."""
    return snapshot.use_extension(DifferentDirectoryExtension)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> Generator[None, None, None]:
    """Enable custom integration."""
    _ = enable_custom_integrations  # unused
    yield


@pytest.fixture(name="platforms")
def mock_platforms() -> list[Platform]:
    """Fixture for platforms loaded by the integration."""
    return []


@pytest.fixture(name="setup_integration")
async def mock_setup_integration(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    platforms: list[Platform],
) -> AsyncGenerator[None, None]:
    """Set up the integration."""

    with patch(f"custom_components.{DOMAIN}.PLATFORMS", platforms):
        assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()
        yield


@pytest.fixture(name="config_entry")
async def mock_config_entry(
    hass: HomeAssistant,
) -> MockConfigEntry:
    """Fixture to create a configuration entry."""
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={},
    )
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry
