"""Tests for the Smart Meter B Route integration init."""

from unittest.mock import Mock

from momonga import EchonetPropertyCode
import pytest

from homeassistant.components.route_b_smart_meter.const import (
    CONF_SUPPORTS_TOTAL_EXPORTED,
    DOMAIN,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry


async def test_async_setup_entry_success(
    hass: HomeAssistant, mock_momonga, mock_config_entry: MockConfigEntry
) -> None:
    """Test successful setup of entry."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


@pytest.mark.parametrize(
    ("supported_properties", "supports_total_exported"),
    [
        ({EchonetPropertyCode.measured_cumulative_energy_reversed}, True),
        (set(), False),
    ],
)
async def test_async_migrate_entry_v1_to_v2(
    hass: HomeAssistant,
    mock_momonga: Mock,
    user_input: dict[str, str],
    supported_properties: set[EchonetPropertyCode],
    supports_total_exported: bool,
) -> None:
    """Test migrating a version 1 entry detects total exported support."""
    mock_momonga.return_value.get_properties_to_get_values.return_value = (
        supported_properties
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=user_input,
        entry_id="01234567890123456789012345F789",
        unique_id="123456",
        version=1,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.version == 2
    assert entry.data[CONF_SUPPORTS_TOTAL_EXPORTED] is supports_total_exported
