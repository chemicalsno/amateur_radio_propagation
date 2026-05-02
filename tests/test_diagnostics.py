"""Tests for the diagnostics module."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.components.diagnostics import REDACTED
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.amateur_radio_propagation.const import (
    CHOICE,
    DOMAIN,
    STATION_CODE,
    Choice,
)
from custom_components.amateur_radio_propagation.diagnostics import (
    async_get_config_entry_diagnostics,
)


async def test_solar_diagnostics(hass):
    """Diagnostics for a Solar entry returns coordinator data and entry info."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CHOICE: Choice.SOLAR},
        title="Solar Data",
        unique_id="Solar Data",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.amateur_radio_propagation.coordinator_solar."
        "SolarCoordinator._async_update_data",
        return_value={"solar_xray": "C1.0", "solar_xray_scale": 100.0},
    ):
        assert await hass.config_entries.async_setup(entry.entry_id) is True
        await hass.async_block_till_done()

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["entry_data"][CHOICE] == Choice.SOLAR
    assert result["coordinator_data"]["solar_xray"] == "C1.0"
    assert result["last_update_success"] is True
    assert result["last_exception"] is None


async def test_muf_diagnostics(hass):
    """Diagnostics for a MUF entry includes station code in entry data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CHOICE: Choice.MUF, STATION_CODE: "BC840"},
        title="Boulder",
        unique_id="BC840",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.amateur_radio_propagation.coordinator_muf."
        "MufCoordinator._async_update_data",
        return_value={"solar_hf_muf_BC840": 12.5},
    ):
        assert await hass.config_entries.async_setup(entry.entry_id) is True
        await hass.async_block_till_done()

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["entry_data"][STATION_CODE] == REDACTED
    assert result["coordinator_data"]["solar_hf_muf_BC840"] == 12.5
    assert result["last_update_success"] is True
