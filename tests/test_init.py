"""Integration setup and teardown tests."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.amateur_radio_propagation.const import (
    CHOICE,
    DOMAIN,
    STATION_CODE,
    Choice,
)


async def test_solar_setup_and_unload(hass):
    """Solar entry loads successfully and unloads cleanly."""
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

    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data is not None

    assert await hass.config_entries.async_unload(entry.entry_id) is True
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_muf_setup_and_unload(hass):
    """MUF entry loads successfully and unloads cleanly (notification patched out)."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CHOICE: Choice.MUF, STATION_CODE: "BC840"},
        title="Boulder",
        unique_id="BC840",
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.amateur_radio_propagation.coordinator_muf."
            "MufCoordinator._async_update_data",
            return_value={"solar_hf_muf_BC840": 12.5},
        ),
        patch(
            "custom_components.amateur_radio_propagation.async_notify_dashboard_ready"
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id) is True
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED

    with patch(
        "custom_components.amateur_radio_propagation.coordinator_muf.async_delete_issue"
    ) as mock_delete:
        assert await hass.config_entries.async_unload(entry.entry_id) is True
        await hass.async_block_till_done()

    mock_delete.assert_called_once_with(
        hass, "amateur_radio_propagation", "stale_BC840"
    )
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_muf_setup_calls_dashboard_notification(hass):
    """async_notify_dashboard_ready is called after successful MUF first refresh."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CHOICE: Choice.MUF, STATION_CODE: "BC840"},
        title="Boulder",
        unique_id="BC840",
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.amateur_radio_propagation.coordinator_muf."
            "MufCoordinator._async_update_data",
            return_value={"solar_hf_muf_BC840": 12.5},
        ),
        patch(
            "custom_components.amateur_radio_propagation.async_notify_dashboard_ready"
        ) as mock_notify,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id) is True
        await hass.async_block_till_done()

    mock_notify.assert_awaited_once_with(hass, entry)


async def test_solar_setup_does_not_call_dashboard_notification(hass):
    """async_notify_dashboard_ready is NOT called for Solar entries."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CHOICE: Choice.SOLAR},
        title="Solar Data",
        unique_id="Solar Data",
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.amateur_radio_propagation.coordinator_solar."
            "SolarCoordinator._async_update_data",
            return_value={"solar_xray": "C1.0"},
        ),
        patch(
            "custom_components.amateur_radio_propagation.async_notify_dashboard_ready"
        ) as mock_notify,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id) is True
        await hass.async_block_till_done()

    mock_notify.assert_not_called()


async def test_setup_retry_on_first_fetch_failure(hass):
    """Failed first refresh puts entry into SETUP_RETRY state."""
    from homeassistant.helpers.update_coordinator import UpdateFailed

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
        side_effect=UpdateFailed("api down"),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id) is False
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY
