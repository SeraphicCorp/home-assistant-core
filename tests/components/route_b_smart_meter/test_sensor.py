"""Tests for the Smart Meter B-Route sensor."""

from unittest.mock import Mock

from freezegun.api import FrozenDateTimeFactory
from momonga import MomongaError
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.route_b_smart_meter.const import DEFAULT_SCAN_INTERVAL
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import EntityRegistry

from tests.common import MockConfigEntry, async_fire_time_changed, snapshot_platform


async def test_route_b_smart_meter_sensor_update(
    hass: HomeAssistant,
    mock_momonga: Mock,
    freezer: FrozenDateTimeFactory,
    entity_registry: EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the BRouteUpdateCoordinator successful behavior."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    freezer.tick(DEFAULT_SCAN_INTERVAL)
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)
    await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_route_b_smart_meter_sensor_no_update(
    hass: HomeAssistant,
    mock_momonga: Mock,
    freezer: FrozenDateTimeFactory,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the BRouteUpdateCoordinator when failing."""

    entity_id = (
        "sensor.route_b_smart_meter_"
        "01234567890123456789012345f789_"
        "instantaneous_current_r_phase"
    )
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity = hass.states.get(entity_id)
    assert entity.state == "1.0"

    mock_momonga.return_value.get_instantaneous_current.side_effect = MomongaError
    freezer.tick(DEFAULT_SCAN_INTERVAL)
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)

    entity = hass.states.get(entity_id)
    assert entity.state is STATE_UNAVAILABLE


async def test_route_b_smart_meter_sensor_none_values(
    hass: HomeAssistant,
    mock_momonga: Mock,
    freezer: FrozenDateTimeFactory,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the BRouteUpdateCoordinator handles None values from API."""
    r_phase_entity_id = (
        "sensor.route_b_smart_meter_"
        "01234567890123456789012345f789_"
        "instantaneous_current_r_phase"
    )
    t_phase_entity_id = (
        "sensor.route_b_smart_meter_"
        "01234567890123456789012345f789_"
        "instantaneous_current_t_phase"
    )
    power_entity_id = (
        "sensor.route_b_smart_meter_01234567890123456789012345f789_instantaneous_power"
    )
    consumption_entity_id = (
        "sensor.route_b_smart_meter_01234567890123456789012345f789_total_consumption"
    )

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get(r_phase_entity_id).state == "1.0"
    assert hass.states.get(t_phase_entity_id).state == "2.0"
    assert hass.states.get(power_entity_id).state == "3.0"
    assert hass.states.get(consumption_entity_id).state == "4.0"

    mock_momonga.return_value.get_instantaneous_current.return_value = {
        "r phase current": None,
        "t phase current": None,
    }
    mock_momonga.return_value.get_instantaneous_power.return_value = None
    mock_momonga.return_value.get_measured_cumulative_energy.return_value = None

    freezer.tick(DEFAULT_SCAN_INTERVAL)
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)

    r_phase_entity = hass.states.get(r_phase_entity_id)
    t_phase_entity = hass.states.get(t_phase_entity_id)
    power_entity = hass.states.get(power_entity_id)
    consumption_entity = hass.states.get(consumption_entity_id)

    assert r_phase_entity.state is STATE_UNAVAILABLE
    assert t_phase_entity.state is STATE_UNAVAILABLE
    assert power_entity.state is STATE_UNAVAILABLE
    assert consumption_entity.state is STATE_UNAVAILABLE


async def test_route_b_smart_meter_sensor_current_returns_none(
    hass: HomeAssistant,
    mock_momonga: Mock,
    freezer: FrozenDateTimeFactory,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the BRouteUpdateCoordinator when get_instantaneous_current returns None."""
    r_phase_entity_id = (
        "sensor.route_b_smart_meter_"
        "01234567890123456789012345f789_"
        "instantaneous_current_r_phase"
    )
    t_phase_entity_id = (
        "sensor.route_b_smart_meter_"
        "01234567890123456789012345f789_"
        "instantaneous_current_t_phase"
    )

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    mock_momonga.return_value.get_instantaneous_current.return_value = None
    mock_momonga.return_value.get_instantaneous_power.return_value = 100.0
    mock_momonga.return_value.get_measured_cumulative_energy.return_value = 50.0

    freezer.tick(DEFAULT_SCAN_INTERVAL)
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)

    r_phase_entity = hass.states.get(r_phase_entity_id)
    t_phase_entity = hass.states.get(t_phase_entity_id)
    power_entity = hass.states.get(
        "sensor.route_b_smart_meter_01234567890123456789012345f789_instantaneous_power"
    )

    assert r_phase_entity.state is STATE_UNAVAILABLE
    assert t_phase_entity.state is STATE_UNAVAILABLE
    assert power_entity.state == "100.0"
