"""Tests for Amateur Radio Propagation sensor entities."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.amateur_radio_propagation.const import (
    ATTRIBUTION_SOLAR,
    CHOICE,
    DOMAIN,
    SENSOR_TYPES,
    STATION_CODE,
    Choice,
)
from custom_components.amateur_radio_propagation.coordinator_muf import MufCoordinator
from custom_components.amateur_radio_propagation.coordinator_solar import (
    SolarCoordinator,
)
from custom_components.amateur_radio_propagation.sensor import (
    HamRadioSensor,
    _muf_descriptions,
)


def _make_entry(
    hass: HomeAssistant,
    choice: Choice,
    data: dict[str, Any] | None = None,
    title: str = "Solar Data",
) -> ConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CHOICE: choice, **(data or {})},
        title=title,
        unique_id=title,
    )
    entry.add_to_hass(hass)
    return entry


def _description(key: str) -> SensorEntityDescription:
    return next(description for description in SENSOR_TYPES if description.key == key)


async def test_native_value_reads_coordinator_data(hass: HomeAssistant) -> None:
    """Sensor native value comes from coordinator data by description key."""
    entry = _make_entry(hass, Choice.SOLAR)
    coordinator = SolarCoordinator(hass, entry)
    coordinator.data = {"solar_xray": "C1.0"}

    sensor = HamRadioSensor(coordinator, entry, _description("solar_xray"))

    assert sensor.native_value == "C1.0"
    assert sensor.available is True


async def test_sensor_unavailable_without_value(hass: HomeAssistant) -> None:
    """Sensor is unavailable when its coordinator key has no value."""
    entry = _make_entry(hass, Choice.SOLAR)
    coordinator = SolarCoordinator(hass, entry)
    coordinator.data = {}

    sensor = HamRadioSensor(coordinator, entry, _description("solar_xray"))

    assert sensor.native_value is None
    assert sensor.available is False


async def test_extra_state_attributes_include_sources_and_latest_alert(
    hass: HomeAssistant,
) -> None:
    """Solar sensors expose attribution, freshness, and alert details."""
    entry = _make_entry(hass, Choice.SOLAR)
    coordinator = SolarCoordinator(hass, entry)
    coordinator.data = {
        "solar_alert_count": 1,
        "solar_alert_message": "ALERT: Geomagnetic Storm warning issued.",
    }
    noaa_time = datetime(2026, 4, 26, 12, 0, tzinfo=dt_util.UTC)
    hamqsl_time = datetime(2026, 4, 26, 9, 0, tzinfo=dt_util.UTC)
    coordinator.last_noaa_success = noaa_time
    coordinator.last_hamqsl_success = hamqsl_time

    sensor = HamRadioSensor(coordinator, entry, _description("solar_alert_count"))
    attrs = sensor.extra_state_attributes

    assert attrs["attribution"] == ATTRIBUTION_SOLAR
    assert attrs["source_updated_noaa"] == noaa_time.isoformat()
    assert attrs["source_updated_hamqsl"] == hamqsl_time.isoformat()
    assert attrs["latest_alert"] == "ALERT: Geomagnetic Storm warning issued."


async def test_muf_sensor_identity_uses_station_specific_key(
    hass: HomeAssistant,
) -> None:
    """MUF entity and unique IDs include the station-specific sensor key."""
    entry = _make_entry(
        hass,
        Choice.MUF,
        data={STATION_CODE: "BC840"},
        title="Boulder",
    )
    coordinator = MufCoordinator(hass, entry)
    coordinator.data = {"solar_hf_muf_BC840": 12.5}

    sensor = HamRadioSensor(coordinator, entry, _muf_descriptions("BC840")[0])

    assert sensor.native_value == 12.5
    assert sensor.entity_id == "sensor.amateur_radio_propagation_solar_hf_muf_bc840"
    assert sensor.unique_id == f"{entry.entry_id}_solar_hf_muf_bc840"


async def test_muf_extra_state_attributes_include_kc2g_freshness(
    hass: HomeAssistant,
) -> None:
    """MUF sensors expose the last successful kc2g update time."""
    entry = _make_entry(
        hass,
        Choice.MUF,
        data={STATION_CODE: "BC840"},
        title="Boulder",
    )
    coordinator = MufCoordinator(hass, entry)
    coordinator.data = {"solar_hf_muf_BC840": 12.5}
    kc2g_time = datetime(2026, 4, 26, 13, 0, tzinfo=dt_util.UTC)
    coordinator.last_kc2g_success = kc2g_time

    sensor = HamRadioSensor(coordinator, entry, _muf_descriptions("BC840")[0])

    assert sensor.extra_state_attributes["source_updated_kc2g"] == kc2g_time.isoformat()
