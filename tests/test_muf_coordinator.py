"""Tests for MufCoordinator."""

from __future__ import annotations

import json
from datetime import timedelta
from unittest.mock import patch

import pytest
from _pytest.logging import LogCaptureFixture
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.amateur_radio_propagation.const import (
    CHOICE,
    CONFIGURATION_URL,
    DOMAIN,
    OPTION_STALE_HOURS,
    STATION_CODE,
    Choice,
)
from custom_components.amateur_radio_propagation.coordinator_muf import (
    MufCoordinator,
    _parse_kc2g_station,
)
from homeassistant.helpers.update_coordinator import UpdateFailed

STATION_CODE_VAL = "BC840"

# Fresh record: timestamp is now
_FRESH_TIME = dt_util.utcnow().isoformat()
# Stale record: timestamp is 4 hours ago
_STALE_TIME = (dt_util.utcnow() - timedelta(hours=4)).isoformat()

KC2G_FRESH = json.dumps(
    [
        {
            "station": {
                "code": "BC840",
                "name": "Boulder",
                "latitude": 40.0,
                "longitude": 254.7,
            },
            "mufd": 12.5,
            "fof2": 5.4,
            "foe": 3.2,
            "cs": 85,
            "foes": 4.1,
            "hmf2": 280.0,
            "tec": 12.3,
            "hme": 95.0,
            "md": 2.8,
            "fof1": None,
            "hmf1": None,
            "scalef2": 50.0,
            "yf2": 80.0,
            "time": _FRESH_TIME,
        }
    ]
)

KC2G_STALE = json.dumps(
    [
        {
            "station": {
                "code": "BC840",
                "name": "Boulder",
                "latitude": 40.0,
                "longitude": 254.7,
            },
            "mufd": 10.0,
            "fof2": 4.0,
            "foe": 2.5,
            "cs": 60,
            "foes": 3.0,
            "hmf2": 260.0,
            "tec": 10.0,
            "hme": 85.0,
            "md": 2.0,
            "fof1": None,
            "hmf1": None,
            "scalef2": 45.0,
            "yf2": 75.0,
            "time": _STALE_TIME,
        }
    ]
)

KC2G_NO_STATION = json.dumps(
    [{"station": {"code": "OTHER", "name": "Other"}, "mufd": 10.0, "time": _FRESH_TIME}]
)


def _make_entry(
    hass: HomeAssistant,
    options: dict[str, int] | None = None,
) -> ConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CHOICE: Choice.MUF, STATION_CODE: STATION_CODE_VAL},
        options=options,
        title="Boulder",
        unique_id=STATION_CODE_VAL,
    )
    entry.add_to_hass(hass)
    return entry


async def test_happy_path_data_keys(hass):
    """Station fields are stored under solar_hf_{field}_{code} keys."""
    coordinator = MufCoordinator(hass, _make_entry(hass))
    assert coordinator.last_kc2g_success is None

    with patch.object(coordinator, "_fetch_text", return_value=KC2G_FRESH):
        data = await coordinator._async_update_data()

    assert data["solar_hf_muf_BC840"] == 12.5
    assert data["solar_hf_fof2_BC840"] == 5.4
    assert data["solar_hf_foe_BC840"] == 3.2
    assert data["solar_hf_cs_BC840"] == 85
    assert data["solar_hf_hmf2_BC840"] == 280.0
    assert data["solar_hf_tec_BC840"] == 12.3
    assert data["solar_hf_foes_BC840"] == 4.1
    assert data["solar_hf_hme_BC840"] == 95.0
    assert data["solar_hf_md_BC840"] == 2.8
    assert data["solar_hf_fof1_BC840"] is None  # absent fields pass through as None
    assert data["solar_hf_hmf1_BC840"] is None
    assert data["solar_hf_scalef2_BC840"] == 50.0
    assert data["solar_hf_yf2_BC840"] == 80.0
    assert coordinator.last_kc2g_success is not None


async def test_station_not_found_raises_update_failed(hass):
    """UpdateFailed raised when configured station is absent from feed."""
    coordinator = MufCoordinator(hass, _make_entry(hass))
    with patch.object(coordinator, "_fetch_text", return_value=KC2G_NO_STATION):
        with pytest.raises(UpdateFailed, match="BC840"):
            await coordinator._async_update_data()


def test_parse_kc2g_station_rejects_wrong_shape() -> None:
    """kc2g parser rejects non-list payloads."""
    with pytest.raises(UpdateFailed, match="did not return a list"):
        _parse_kc2g_station({"station": {}}, STATION_CODE_VAL)


def test_parse_kc2g_station_ignores_malformed_records() -> None:
    """kc2g parser skips malformed records while searching for the station."""
    record = _parse_kc2g_station(
        [
            "bad",
            {"station": "bad"},
            {"station": {"code": STATION_CODE_VAL}, "mufd": 12.5},
        ],
        STATION_CODE_VAL,
    )

    assert record["mufd"] == 12.5


async def test_fresh_data_deletes_issue(hass):
    """Fresh station data deletes any existing staleness repair issue."""
    coordinator = MufCoordinator(hass, _make_entry(hass))
    with (
        patch.object(coordinator, "_fetch_text", return_value=KC2G_FRESH),
        patch(
            "custom_components.amateur_radio_propagation.coordinator_muf."
            "async_delete_issue"
        ) as mock_delete,
    ):
        await coordinator._async_update_data()

    mock_delete.assert_called_once_with(
        hass, "amateur_radio_propagation", "stale_BC840"
    )


async def test_stale_data_creates_issue(hass):
    """Stale station data (>3 hr old) creates a repair issue."""
    coordinator = MufCoordinator(hass, _make_entry(hass))
    with (
        patch.object(coordinator, "_fetch_text", return_value=KC2G_STALE),
        patch(
            "custom_components.amateur_radio_propagation.coordinator_muf."
            "async_create_issue"
        ) as mock_create,
    ):
        await coordinator._async_update_data()

    mock_create.assert_called_once()
    args = mock_create.call_args
    assert args.args[2] == "stale_BC840"
    assert args.kwargs["translation_key"] == "stale_station_data"
    assert args.kwargs["translation_placeholders"]["url"] == CONFIGURATION_URL


async def test_stale_option_threshold_is_honored(hass: HomeAssistant) -> None:
    """A station older than the default but newer than the option stays fresh."""
    coordinator = MufCoordinator(hass, _make_entry(hass, {OPTION_STALE_HOURS: 6}))
    with (
        patch.object(coordinator, "_fetch_text", return_value=KC2G_STALE),
        patch(
            "custom_components.amateur_radio_propagation.coordinator_muf."
            "async_delete_issue"
        ) as mock_delete,
    ):
        await coordinator._async_update_data()

    mock_delete.assert_called_once_with(
        hass, "amateur_radio_propagation", "stale_BC840"
    )


async def test_network_error_raises_update_failed(hass):
    """aiohttp errors are wrapped in UpdateFailed."""
    import aiohttp

    coordinator = MufCoordinator(hass, _make_entry(hass))
    with patch.object(
        coordinator, "_fetch_text", side_effect=aiohttp.ClientError("down")
    ):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()


async def test_kc2g_failure_logs_once_until_recovery(
    hass: HomeAssistant, caplog: LogCaptureFixture
) -> None:
    """Repeated kc2g failures log once and recovery is logged once."""
    coordinator = MufCoordinator(hass, _make_entry(hass))

    with caplog.at_level(
        "DEBUG",
        logger="custom_components.amateur_radio_propagation.coordinator_muf",
    ):
        coordinator._log_kc2g_unavailable(UpdateFailed("down"))
        coordinator._log_kc2g_unavailable(UpdateFailed("still down"))
        coordinator._log_kc2g_recovered()

    assert "MUF update failed, keeping previous data: down" in caplog.messages
    assert (
        "MUF update still failing, keeping previous data: still down" in caplog.messages
    )
    assert "MUF source recovered: kc2g" in caplog.messages


async def test_dismiss_issue_helper(hass):
    """dismiss_issue() calls async_delete_issue with the correct args."""
    coordinator = MufCoordinator(hass, _make_entry(hass))
    with patch(
        "custom_components.amateur_radio_propagation.coordinator_muf.async_delete_issue"
    ) as mock_delete:
        coordinator.dismiss_issue()

    mock_delete.assert_called_once_with(
        hass, "amateur_radio_propagation", "stale_BC840"
    )
