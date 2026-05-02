"""Tests for SolarCoordinator."""

from __future__ import annotations

import json
import logging
from datetime import timedelta
from unittest.mock import patch

import pytest
from _pytest.logging import LogCaptureFixture
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.amateur_radio_propagation.const import CHOICE, DOMAIN, Choice
from custom_components.amateur_radio_propagation.coordinator_solar import (
    SolarCoordinator,
    _CIRCUIT_THRESHOLD,
    _parse_hamqsl,
    _parse_noaa_alerts,
    _parse_noaa_kp,
    _parse_noaa_probabilities,
    _parse_noaa_scales,
    _parse_noaa_xray,
    _parse_noaa_plasma,  # new
    _parse_noaa_mag,  # new
    _parse_noaa_kp_forecast,
    _parse_noaa_dst,
    _parse_noaa_predicted_a,
    _parse_noaa_predicted_sfi,
    _parse_noaa_solar_regions,
)
from homeassistant.helpers.update_coordinator import UpdateFailed

NOAA_PAYLOAD = json.dumps(
    [
        {
            "current_class": "C1.5",
            "max_class": "C2.0",
            "begin_class": "C1.0",
            "end_class": "C1.5",
            "current_ratio": 1.5,
        }
    ]
)

HAMQSL_PAYLOAD = """<?xml version="1.0" encoding="UTF-8"?>
<solar>
  <solardata>
    <solarflux>175</solarflux>
    <sunspots>134</sunspots>
    <aindex>7</aindex>
    <kindex>2</kindex>
    <magneticfield>-5.2</magneticfield>
    <solarwind>450</solarwind>
    <fof2>5.4</fof2>
    <geomagfield>Active</geomagfield>
    <signalnoise>S2</signalnoise>
    <aurora>3</aurora>
    <latdegree>65.5</latdegree>
    <calculatedconditions>
      <band name="80m-40m" time="day">Good</band>
      <band name="80m-40m" time="night">Poor</band>
      <band name="30m-20m" time="day">Fair</band>
      <band name="30m-20m" time="night">Poor</band>
      <band name="17m-15m" time="day">Good</band>
      <band name="17m-15m" time="night">Poor</band>
      <band name="12m-10m" time="day">Fair</band>
      <band name="12m-10m" time="night">Poor</band>
    </calculatedconditions>
    <calculatedvhfconditions>
      <phenomenon name="vhf-aurora" location="northern_hemi">No</phenomenon>
      <phenomenon name="E-Skip" location="europe">No</phenomenon>
      <phenomenon name="E-Skip" location="north_america">No</phenomenon>
      <phenomenon name="E-Skip" location="europe_6m">No</phenomenon>
      <phenomenon name="E-Skip" location="europe_4m">No</phenomenon>
    </calculatedvhfconditions>
  </solardata>
</solar>"""


def _make_entry(hass: HomeAssistant) -> ConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CHOICE: Choice.SOLAR},
        title="Solar Data",
        unique_id="Solar Data",
    )
    entry.add_to_hass(hass)
    return entry


async def _mock_fetch_text(url: str) -> str:
    if "swpc.noaa.gov" in url:
        return NOAA_PAYLOAD
    if "hamqsl.com" in url:
        return HAMQSL_PAYLOAD
    raise ValueError(f"Unexpected URL: {url}")


async def test_happy_path_noaa_fields(hass):
    """NOAA data parsed correctly: xray class, scale, and extras."""
    coordinator = SolarCoordinator(hass, _make_entry(hass))
    with patch.object(coordinator, "_fetch_text", side_effect=_mock_fetch_text):
        data = await coordinator._async_update_data()

    assert data["solar_xray"] == "C1.5"
    assert data["solar_xray_scale"] == 150.0
    assert data["solar_xray_peak_class"] == "C2.0"
    assert data["solar_xray_begin_class"] == "C1.0"
    assert data["solar_xray_end_class"] == "C1.5"
    assert data["solar_xray_current_ratio"] == 1.5


async def test_happy_path_hamqsl_scalars(hass):
    """hamqsl scalar fields parsed correctly on first call (slow poll due)."""
    coordinator = SolarCoordinator(hass, _make_entry(hass))
    with patch.object(coordinator, "_fetch_text", side_effect=_mock_fetch_text):
        data = await coordinator._async_update_data()

    assert data["solar_flux_index"] == 175.0
    assert data["solar_sunspots"] == 134.0
    assert data["solar_a_index"] == 7.0
    assert data["solar_k_index"] == 2.0
    assert data["solar_fof2"] == 5.4
    assert data["solar_geomag_field"] == "Active"
    assert data["solar_aurora_activity"] == 3.0
    assert data["solar_aurora_latitude"] == 65.5


async def test_happy_path_hamqsl_bands(hass):
    """hamqsl band conditions parsed correctly."""
    coordinator = SolarCoordinator(hass, _make_entry(hass))
    with patch.object(coordinator, "_fetch_text", side_effect=_mock_fetch_text):
        data = await coordinator._async_update_data()

    assert data["solar_hf_80_40_day"] == "Good"
    assert data["solar_hf_80_40_night"] == "Poor"
    assert data["solar_hf_30_20_day"] == "Fair"
    assert data["solar_vhf_aurora"] == "No"
    assert data["solar_vhf_eskip_eu"] == "No"


async def test_slow_poll_skipped_within_interval(hass):
    """hamqsl is NOT fetched if last slow update was recent."""
    coordinator = SolarCoordinator(hass, _make_entry(hass))
    coordinator._last_slow_update = dt_util.utcnow()  # just ran

    noaa_called = False
    hamqsl_called = False

    async def track_fetch(url: str) -> str:
        nonlocal noaa_called, hamqsl_called
        if "swpc.noaa.gov" in url:
            noaa_called = True
            return NOAA_PAYLOAD
        if "hamqsl.com" in url:
            hamqsl_called = True
            return HAMQSL_PAYLOAD
        raise ValueError(url)

    with patch.object(coordinator, "_fetch_text", side_effect=track_fetch):
        await coordinator._async_update_data()

    assert noaa_called is True
    assert hamqsl_called is False


async def test_slow_poll_runs_after_interval(hass):
    """hamqsl IS fetched once the 3-hour window has elapsed."""
    coordinator = SolarCoordinator(hass, _make_entry(hass))
    coordinator._last_slow_update = dt_util.utcnow() - timedelta(hours=4)

    hamqsl_called = False

    async def track_fetch(url: str) -> str:
        nonlocal hamqsl_called
        if "hamqsl.com" in url:
            hamqsl_called = True
            return HAMQSL_PAYLOAD
        return NOAA_PAYLOAD

    with patch.object(coordinator, "_fetch_text", side_effect=track_fetch):
        await coordinator._async_update_data()

    assert hamqsl_called is True


async def test_bad_http_status_raises_update_failed(hass):
    """Non-200 HTTP status raises UpdateFailed."""
    coordinator = SolarCoordinator(hass, _make_entry(hass))

    async def bad_fetch(url: str) -> str:
        raise UpdateFailed("HTTP 503")

    with patch.object(coordinator, "_fetch_text", side_effect=bad_fetch):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()


async def test_malformed_noaa_json_raises_update_failed(hass):
    """Invalid JSON from NOAA raises UpdateFailed."""
    coordinator = SolarCoordinator(hass, _make_entry(hass))

    async def bad_fetch(url: str) -> str:
        return "not json at all"

    with patch.object(coordinator, "_fetch_text", side_effect=bad_fetch):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()


async def test_xray_scale_x_class(hass):
    """X-class flare scale calculated correctly (X2.5 → 25000)."""
    coordinator = SolarCoordinator(hass, _make_entry(hass))
    payload = json.dumps(
        [
            {
                "current_class": "X2.5",
                "max_class": None,
                "begin_class": None,
                "end_class": None,
                "current_ratio": None,
            }
        ]
    )

    async def fetch(url: str) -> str:
        if "swpc.noaa.gov" in url:
            return payload
        return HAMQSL_PAYLOAD

    with patch.object(coordinator, "_fetch_text", side_effect=fetch):
        data = await coordinator._async_update_data()

    assert data["solar_xray"] == "X2.5"
    assert data["solar_xray_scale"] == 25000.0


def test_parse_noaa_xray_rejects_missing_current_class() -> None:
    """NOAA X-ray parser rejects entries without current_class."""
    with pytest.raises(UpdateFailed, match="current_class"):
        _parse_noaa_xray([{"max_class": "C1.0"}])


def test_parse_noaa_xray_rejects_wrong_shape() -> None:
    """NOAA X-ray parser rejects non-list payloads."""
    with pytest.raises(UpdateFailed, match="payload"):
        _parse_noaa_xray({"current_class": "C1.0"})


def test_parse_noaa_scales_rejects_wrong_shape() -> None:
    """NOAA scales parser rejects non-object payloads."""
    with pytest.raises(UpdateFailed, match="payload"):
        _parse_noaa_scales([])


def test_parse_noaa_scales_allows_missing_individual_scales() -> None:
    """NOAA scales parser keeps keys present even when a scale block is absent."""
    parsed = _parse_noaa_scales({"0": {"G": {"Scale": "G1"}}})

    assert parsed["solar_geomag_storm"] == "G1"
    assert parsed["solar_radiation_storm"] is None
    assert parsed["solar_radio_blackout"] is None


def test_parse_noaa_probabilities_rejects_empty_payload() -> None:
    """NOAA probabilities parser rejects empty payloads."""
    with pytest.raises(UpdateFailed, match="probabilities"):
        _parse_noaa_probabilities([])


def test_parse_noaa_probabilities_keeps_missing_fields_as_none() -> None:
    """NOAA probabilities parser keeps expected keys even for partial entries."""
    parsed = _parse_noaa_probabilities([{"m_class_1_day": 45}])

    assert parsed["solar_flare_prob_m1"] == 45
    assert parsed["solar_flare_prob_x1"] is None
    assert parsed["solar_flare_prob_m3"] is None
    assert parsed["solar_flare_prob_x3"] is None
    assert parsed["solar_pca"] is None


def test_parse_noaa_kp_rejects_unsupported_entry_shape() -> None:
    """NOAA K-index parser rejects unsupported entry shapes."""
    with pytest.raises(UpdateFailed, match="unsupported"):
        _parse_noaa_kp(["bad"])


def test_parse_noaa_alerts_rejects_non_object_entries() -> None:
    """NOAA alerts parser rejects malformed alert entries."""
    with pytest.raises(UpdateFailed, match="alert entry"):
        _parse_noaa_alerts(["bad"])


def test_parse_hamqsl_rejects_missing_solardata() -> None:
    """hamqsl parser rejects XML missing the solardata element."""
    with pytest.raises(UpdateFailed, match="solardata"):
        _parse_hamqsl("<solar />")


def test_parse_hamqsl_numeric_no_report_becomes_none() -> None:
    """hamqsl numeric parser converts non-numeric numeric fields to None."""
    parsed = _parse_hamqsl(
        """
        <solar>
          <solardata>
            <solarflux>No Report</solarflux>
            <geomagfield>Quiet</geomagfield>
          </solardata>
        </solar>
        """
    )

    assert parsed["solar_flux_index"] is None
    assert parsed["solar_geomag_field"] == "Quiet"


async def test_empty_noaa_response_logs_warning_not_raises(hass, caplog):
    """Empty list from NOAA logs a warning but doesn't fail the coordinator.

    Individual endpoint failures are swallowed so other sensors stay available.
    UpdateFailed is only raised if we have no data at all from any source.
    """
    coordinator = SolarCoordinator(hass, _make_entry(hass))

    async def fetch(url: str) -> str:
        return "[]"  # empty list — entries[0] raises IndexError on NOAA X-ray

    with caplog.at_level(
        logging.WARNING,
        logger="custom_components.amateur_radio_propagation.coordinator_solar",
    ):
        with patch.object(coordinator, "_fetch_text", side_effect=fetch):
            result = await coordinator._async_update_data()

    assert any("NOAA X-ray" in msg for msg in caplog.messages)
    # alert endpoint succeeds (returns empty list = 0 alerts), so data is not empty
    assert result.get("solar_alert_count") == 0


# ---------------------------------------------------------------------------
# New NOAA endpoint tests
# ---------------------------------------------------------------------------

SCALES_PAYLOAD = json.dumps(
    {
        "0": {
            "G": {"Scale": "G2"},
            "S": {"Scale": "S1"},
            "R": {"Scale": "R0"},
        }
    }
)

PROBABILITIES_PAYLOAD = json.dumps(
    [
        {
            "m_class_1_day": 45,
            "x_class_1_day": 10,
            "m_class_3_day": 60,
            "x_class_3_day": 20,
            "polar_cap_absorption": 5,
        }
    ]
)

KP_PAYLOAD_ARRAY = json.dumps(
    [
        ["2024-01-01T00:00:00Z", 2.0, 2.33, "estimated"],
    ]
)

KP_PAYLOAD_DICT = json.dumps(
    [
        {"time_tag": "2024-01-01T00:00:00Z", "estimated_kp": 3.67},
    ]
)

ALERTS_PAYLOAD = json.dumps(
    [
        {"message": "ALERT: Geomagnetic Storm warning issued."},
        {"message": "WATCH: Solar radiation storm."},
    ]
)


async def _full_fetch(url: str) -> str:
    """Return all endpoint payloads based on URL."""
    if "xray-flares" in url:
        return NOAA_PAYLOAD
    if "noaa-scales" in url:
        return SCALES_PAYLOAD
    if "solar_probabilities" in url:
        return PROBABILITIES_PAYLOAD
    if "planetary_k_index_1m" in url:
        return KP_PAYLOAD_ARRAY
    if "alerts" in url:
        return ALERTS_PAYLOAD
    if "hamqsl.com" in url:
        return HAMQSL_PAYLOAD
    raise ValueError(f"Unexpected URL: {url}")


async def test_noaa_scales_parsed(hass):
    """NOAA space weather scales parsed into the three scale sensors."""
    coordinator = SolarCoordinator(hass, _make_entry(hass))
    with patch.object(coordinator, "_fetch_text", side_effect=_full_fetch):
        data = await coordinator._async_update_data()

    assert data["solar_geomag_storm"] == "G2"
    assert data["solar_radiation_storm"] == "S1"
    assert data["solar_radio_blackout"] == "R0"


async def test_noaa_probabilities_parsed(hass):
    """NOAA flare probabilities and PCA parsed correctly."""
    coordinator = SolarCoordinator(hass, _make_entry(hass))
    with patch.object(coordinator, "_fetch_text", side_effect=_full_fetch):
        data = await coordinator._async_update_data()

    assert data["solar_flare_prob_m1"] == 45
    assert data["solar_flare_prob_x1"] == 10
    assert data["solar_flare_prob_m3"] == 60
    assert data["solar_flare_prob_x3"] == 20
    assert data["solar_pca"] == 5


async def test_noaa_kp_array_format(hass):
    """Kp endpoint returns array-of-arrays; third element is estimated_kp."""
    coordinator = SolarCoordinator(hass, _make_entry(hass))
    with patch.object(coordinator, "_fetch_text", side_effect=_full_fetch):
        data = await coordinator._async_update_data()

    assert data["solar_kp_estimated"] == 2.33


async def test_noaa_kp_dict_format(hass):
    """Kp endpoint dict format also parsed correctly."""
    coordinator = SolarCoordinator(hass, _make_entry(hass))

    async def fetch_dict_kp(url: str) -> str:
        if "planetary_k_index_1m" in url:
            return KP_PAYLOAD_DICT
        return await _full_fetch(url)

    with patch.object(coordinator, "_fetch_text", side_effect=fetch_dict_kp):
        data = await coordinator._async_update_data()

    assert data["solar_kp_estimated"] == 3.67


async def test_noaa_alerts_parsed(hass):
    """Alerts count and latest message parsed correctly."""
    coordinator = SolarCoordinator(hass, _make_entry(hass))
    with patch.object(coordinator, "_fetch_text", side_effect=_full_fetch):
        data = await coordinator._async_update_data()

    assert data["solar_alert_count"] == 2
    assert "Geomagnetic Storm" in data["solar_alert_message"]


# ---------------------------------------------------------------------------
# Freshness timestamp tests
# ---------------------------------------------------------------------------


async def test_last_noaa_success_set_on_xray_success(hass):
    """last_noaa_success is updated when NOAA X-ray fetches successfully."""
    coordinator = SolarCoordinator(hass, _make_entry(hass))
    assert coordinator.last_noaa_success is None

    with patch.object(coordinator, "_fetch_text", side_effect=_full_fetch):
        await coordinator._async_update_data()

    assert coordinator.last_noaa_success is not None


async def test_last_hamqsl_success_set_on_slow_poll(hass):
    """last_hamqsl_success is updated after a successful hamqsl fetch."""
    coordinator = SolarCoordinator(hass, _make_entry(hass))
    assert coordinator.last_hamqsl_success is None

    with patch.object(coordinator, "_fetch_text", side_effect=_full_fetch):
        await coordinator._async_update_data()

    assert coordinator.last_hamqsl_success is not None


async def test_last_noaa_success_not_set_when_xray_fails(hass):
    """last_noaa_success is NOT updated when NOAA X-ray endpoint fails."""
    coordinator = SolarCoordinator(hass, _make_entry(hass))

    async def fetch_no_xray(url: str) -> str:
        if "xray-flares" in url:
            raise UpdateFailed("simulated failure")
        return await _full_fetch(url)

    with patch.object(coordinator, "_fetch_text", side_effect=fetch_no_xray):
        await coordinator._async_update_data()

    assert coordinator.last_noaa_success is None


async def test_solar_source_failure_logs_once_until_recovery(
    hass: HomeAssistant, caplog: LogCaptureFixture
) -> None:
    """Repeated source failures log once and recovery is logged once."""
    coordinator = SolarCoordinator(hass, _make_entry(hass))

    with caplog.at_level(
        logging.DEBUG,
        logger="custom_components.amateur_radio_propagation.coordinator_solar",
    ):
        coordinator._log_source_unavailable("NOAA X-ray", UpdateFailed("down"))
        coordinator._log_source_unavailable("NOAA X-ray", UpdateFailed("still down"))
        coordinator._log_source_recovered("NOAA X-ray")

    assert "Solar update skipping NOAA X-ray: down" in caplog.messages
    assert "Solar update still skipping NOAA X-ray: still down" in caplog.messages
    assert "Solar source recovered: NOAA X-ray" in caplog.messages


# ---------------------------------------------------------------------------
# Data carry-forward tests
# ---------------------------------------------------------------------------


async def test_previous_data_preserved_on_partial_failure(hass):
    """Data from previous cycle is preserved when a source fails this cycle."""
    coordinator = SolarCoordinator(hass, _make_entry(hass))
    # Pre-seed coordinator.data as if a previous cycle ran
    coordinator.data = {"solar_flux_index": 175.0, "solar_xray": "C1.5"}

    async def fetch_all_fail(url: str) -> str:
        raise UpdateFailed("all failing this cycle")

    with patch.object(coordinator, "_fetch_text", side_effect=fetch_all_fail):
        # Should NOT raise — previous data exists
        data = await coordinator._async_update_data()

    assert data["solar_flux_index"] == 175.0
    assert data["solar_xray"] == "C1.5"


async def test_update_failed_when_no_data_at_all(hass):
    """UpdateFailed raised if all sources fail AND there is no previous data."""
    coordinator = SolarCoordinator(hass, _make_entry(hass))
    assert coordinator.data is None

    async def fetch_all_fail(url: str) -> str:
        raise UpdateFailed("all failing")

    with patch.object(coordinator, "_fetch_text", side_effect=fetch_all_fail):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Circuit breaker tests
# ---------------------------------------------------------------------------


async def test_circuit_opens_after_threshold_failures(hass):
    """Circuit opens for a source after _CIRCUIT_THRESHOLD consecutive failures."""
    coordinator = SolarCoordinator(hass, _make_entry(hass))
    now = dt_util.utcnow()

    for _ in range(_CIRCUIT_THRESHOLD):
        coordinator._circuit_record_failure("NOAA X-ray", now)

    assert coordinator._circuit_is_open("NOAA X-ray", now)


async def test_circuit_does_not_open_below_threshold(hass):
    """Circuit stays closed if failures are below threshold."""
    coordinator = SolarCoordinator(hass, _make_entry(hass))
    now = dt_util.utcnow()

    for _ in range(_CIRCUIT_THRESHOLD - 1):
        coordinator._circuit_record_failure("NOAA X-ray", now)

    assert not coordinator._circuit_is_open("NOAA X-ray", now)


async def test_circuit_clears_on_success(hass):
    """Circuit resets fully after a successful fetch."""
    coordinator = SolarCoordinator(hass, _make_entry(hass))
    now = dt_util.utcnow()

    for _ in range(_CIRCUIT_THRESHOLD):
        coordinator._circuit_record_failure("NOAA X-ray", now)

    assert coordinator._circuit_is_open("NOAA X-ray", now)

    coordinator._circuit_clear("NOAA X-ray")
    assert not coordinator._circuit_is_open("NOAA X-ray", now)
    assert "NOAA X-ray" not in coordinator._circuit_failures


async def test_open_circuit_skips_source(hass, caplog):
    """A source whose circuit is open is skipped during _async_update_data."""
    coordinator = SolarCoordinator(hass, _make_entry(hass))
    now = dt_util.utcnow()

    # Force the X-ray circuit open
    for _ in range(_CIRCUIT_THRESHOLD):
        coordinator._circuit_record_failure("NOAA X-ray", now)

    xray_called = False

    async def fetch_tracking(url: str) -> str:
        nonlocal xray_called
        if "xray-flares" in url:
            xray_called = True
        return await _full_fetch(url)

    with caplog.at_level(
        logging.DEBUG,
        logger="custom_components.amateur_radio_propagation.coordinator_solar",
    ):
        with patch.object(coordinator, "_fetch_text", side_effect=fetch_tracking):
            await coordinator._async_update_data()

    assert not xray_called
    assert any("Circuit open" in msg for msg in caplog.messages)


async def test_circuit_auto_resets_after_cooldown(hass):
    """Circuit auto-resets once the cooldown period has elapsed."""
    coordinator = SolarCoordinator(hass, _make_entry(hass))
    now = dt_util.utcnow()

    for _ in range(_CIRCUIT_THRESHOLD):
        coordinator._circuit_record_failure("NOAA X-ray", now)

    assert coordinator._circuit_is_open("NOAA X-ray", now)

    # Check 2 hours in the future — past the 1-hour cooldown
    future = now + timedelta(hours=2)
    assert not coordinator._circuit_is_open("NOAA X-ray", future)
    assert "NOAA X-ray" not in coordinator._circuit_failures


# ---------------------------------------------------------------------------
# Repair issue tests
# ---------------------------------------------------------------------------


async def test_repair_issue_raised_when_noaa_stale(hass):
    """Repair issue created when NOAA X-ray hasn't succeeded for 1+ hour."""
    coordinator = SolarCoordinator(hass, _make_entry(hass))
    # Simulate last success 2 hours ago
    coordinator.last_noaa_success = dt_util.utcnow() - timedelta(hours=2)
    now = dt_util.utcnow()

    with (
        patch(
            "custom_components.amateur_radio_propagation.coordinator_solar.async_create_issue"
        ) as mock_create,
        patch(
            "custom_components.amateur_radio_propagation.coordinator_solar.async_delete_issue"
        ),
    ):
        coordinator._check_noaa_staleness(now)

    mock_create.assert_called_once()
    call_kwargs = mock_create.call_args
    assert call_kwargs.args[2] == "stale_noaa"
    assert call_kwargs.kwargs["translation_placeholders"]["url"] == (
        "https://www.swpc.noaa.gov/"
    )


async def test_repair_issue_cleared_when_noaa_fresh(hass):
    """Repair issue deleted when NOAA X-ray succeeded recently."""
    coordinator = SolarCoordinator(hass, _make_entry(hass))
    # Last success just now
    coordinator.last_noaa_success = dt_util.utcnow()
    now = dt_util.utcnow()

    with (
        patch(
            "custom_components.amateur_radio_propagation.coordinator_solar.async_create_issue"
        ) as mock_create,
        patch(
            "custom_components.amateur_radio_propagation.coordinator_solar.async_delete_issue"
        ) as mock_delete,
    ):
        coordinator._check_noaa_staleness(now)

    mock_create.assert_not_called()
    mock_delete.assert_called_once_with(hass, DOMAIN, "stale_noaa")


async def test_repair_issue_uses_started_at_when_no_success(hass):
    """When NOAA has never succeeded, _started_at is used as reference time."""
    coordinator = SolarCoordinator(hass, _make_entry(hass))
    assert coordinator.last_noaa_success is None

    # Simulate coordinator started 90 minutes ago
    coordinator._started_at = dt_util.utcnow() - timedelta(minutes=90)
    now = dt_util.utcnow()

    with (
        patch(
            "custom_components.amateur_radio_propagation.coordinator_solar.async_create_issue"
        ) as mock_create,
        patch(
            "custom_components.amateur_radio_propagation.coordinator_solar.async_delete_issue"
        ),
    ):
        coordinator._check_noaa_staleness(now)

    mock_create.assert_called_once()


# ---------------------------------------------------------------------------
# Solar wind plasma / mag parse tests
# ---------------------------------------------------------------------------


def test_parse_noaa_plasma_returns_density_and_speed():
    """Plasma parse extracts density and speed from last data row."""
    entries = [
        ["time_tag", "density", "speed", "temperature"],
        ["2026-05-01 19:00:00.000", "1.24", "441.7", "70000"],
        ["2026-05-01 19:19:00.000", "0.86", "444.1", "72052"],
    ]
    result = _parse_noaa_plasma(entries)
    assert result["solar_wind_density"] == 0.86
    assert result["solar_wind_speed_noaa"] == 444.1


def test_parse_noaa_plasma_single_data_row():
    """Plasma parse works with exactly one data row."""
    entries = [
        ["time_tag", "density", "speed", "temperature"],
        ["2026-05-01 00:00:00.000", "5.0", "350.0", "40000"],
    ]
    result = _parse_noaa_plasma(entries)
    assert result["solar_wind_density"] == 5.0
    assert result["solar_wind_speed_noaa"] == 350.0


def test_parse_noaa_plasma_empty_raises():
    """Empty plasma payload raises UpdateFailed."""
    with pytest.raises(UpdateFailed):
        _parse_noaa_plasma([])


def test_parse_noaa_plasma_header_only_raises():
    """Plasma payload with only a header row raises UpdateFailed."""
    with pytest.raises(UpdateFailed):
        _parse_noaa_plasma([["time_tag", "density", "speed", "temperature"]])


def test_parse_noaa_plasma_null_values_return_none():
    """Plasma parse returns None for sensor values when NOAA sends null data."""
    entries = [
        ["time_tag", "density", "speed", "temperature"],
        ["2026-05-01 00:00:00.000", None, None, None],
    ]
    result = _parse_noaa_plasma(entries)
    assert result["solar_wind_density"] is None
    assert result["solar_wind_speed_noaa"] is None


def test_parse_noaa_mag_returns_bz_and_bt():
    """Mag parse extracts bz_gsm and bt from last data row."""
    entries = [
        ["time_tag", "bx_gsm", "by_gsm", "bz_gsm", "lon_gsm", "lat_gsm", "bt"],
        ["2026-05-01 19:19:00.000", "0.72", "-4.62", "0.39", "278.82", "4.82", "4.69"],
    ]
    result = _parse_noaa_mag(entries)
    assert result["solar_bz_noaa"] == 0.39
    assert result["solar_wind_bt"] == 4.69


def test_parse_noaa_mag_negative_bz():
    """Mag parse handles negative Bz correctly."""
    entries = [
        ["time_tag", "bx_gsm", "by_gsm", "bz_gsm", "lon_gsm", "lat_gsm", "bt"],
        ["2026-05-01 20:00:00.000", "-1.0", "2.0", "-8.5", "270.0", "3.0", "9.2"],
    ]
    result = _parse_noaa_mag(entries)
    assert result["solar_bz_noaa"] == -8.5
    assert result["solar_wind_bt"] == 9.2


def test_parse_noaa_mag_empty_raises():
    """Empty mag payload raises UpdateFailed."""
    with pytest.raises(UpdateFailed):
        _parse_noaa_mag([])


def test_parse_noaa_mag_short_row_raises():
    """Mag row with fewer than 7 columns raises UpdateFailed."""
    with pytest.raises(UpdateFailed):
        _parse_noaa_mag(
            [
                ["time_tag", "bx_gsm", "by_gsm", "bz_gsm"],
                ["2026-05-01 00:00:00.000", "0.0", "0.0", "-2.0"],
            ]
        )


# ---------------------------------------------------------------------------
# Integration test: plasma + mag fields flow through coordinator
# ---------------------------------------------------------------------------

PLASMA_PAYLOAD = json.dumps(
    [
        ["time_tag", "density", "speed", "temperature"],
        ["2026-05-01 00:00:00.000", "1.0", "400.0", "50000"],
        ["2026-05-01 00:19:00.000", "2.5", "500.0", "60000"],
    ]
)

MAG_PAYLOAD = json.dumps(
    [
        ["time_tag", "bx_gsm", "by_gsm", "bz_gsm", "lon_gsm", "lat_gsm", "bt"],
        ["2026-05-01 00:00:00.000", "1.0", "2.0", "-5.5", "270.0", "3.0", "6.1"],
        ["2026-05-01 00:19:00.000", "0.5", "-3.0", "-8.2", "260.0", "4.0", "8.7"],
    ]
)


async def test_plasma_mag_fields_in_coordinator(hass):
    """Plasma and mag fields flow through _async_update_data correctly."""
    coordinator = SolarCoordinator(hass, _make_entry(hass))

    async def mock_fetch(url: str) -> str:
        if "plasma-2-hour" in url:
            return PLASMA_PAYLOAD
        if "mag-2-hour" in url:
            return MAG_PAYLOAD
        if "swpc.noaa.gov" in url:
            return NOAA_PAYLOAD
        if "hamqsl.com" in url:
            return HAMQSL_PAYLOAD
        raise ValueError(f"Unexpected URL: {url}")

    with patch.object(coordinator, "_fetch_text", side_effect=mock_fetch):
        data = await coordinator._async_update_data()

    assert data["solar_wind_density"] == 2.5
    assert data["solar_wind_speed_noaa"] == 500.0
    assert data["solar_bz_noaa"] == -8.2
    assert data["solar_wind_bt"] == 8.7


# ---------------------------------------------------------------------------
# KP forecast / DST parse unit tests
# ---------------------------------------------------------------------------


def test_parse_noaa_kp_forecast_returns_first_predicted():
    """KP forecast parse returns kp from first predicted entry."""
    entries = [
        {
            "time_tag": "2026-05-01 18:00:00",
            "kp": 3.0,
            "observed": "observed",
            "noaa_scale": None,
        },
        {
            "time_tag": "2026-05-01 21:00:00",
            "kp": 2.67,
            "observed": "predicted",
            "noaa_scale": None,
        },
        {
            "time_tag": "2026-05-02 00:00:00",
            "kp": 2.0,
            "observed": "predicted",
            "noaa_scale": None,
        },
    ]
    result = _parse_noaa_kp_forecast(entries)
    assert result["solar_kp_forecast"] == 2.67


def test_parse_noaa_kp_forecast_no_predicted_returns_none():
    """KP forecast parse returns None when no predicted entry exists."""
    entries = [
        {
            "time_tag": "2026-05-01 18:00:00",
            "kp": 3.0,
            "observed": "observed",
            "noaa_scale": None,
        },
    ]
    result = _parse_noaa_kp_forecast(entries)
    assert result["solar_kp_forecast"] is None


def test_parse_noaa_kp_forecast_empty_raises():
    """Empty KP forecast payload raises UpdateFailed."""
    with pytest.raises(UpdateFailed):
        _parse_noaa_kp_forecast([])


def test_parse_noaa_kp_forecast_predicted_kp_is_none():
    """KP forecast parse returns None when predicted entry has null kp."""
    entries = [
        {
            "time_tag": "2026-05-01 21:00:00",
            "kp": None,
            "observed": "predicted",
            "noaa_scale": None,
        }
    ]
    result = _parse_noaa_kp_forecast(entries)
    assert result["solar_kp_forecast"] is None


def test_parse_noaa_dst_returns_last_entry():
    """DST parse returns dst from last entry."""
    entries = [
        {"time_tag": "2026-05-01 16:00:00", "dst": -16},
        {"time_tag": "2026-05-01 17:00:00", "dst": -12},
        {"time_tag": "2026-05-01 19:00:00", "dst": -8},
    ]
    result = _parse_noaa_dst(entries)
    assert result["solar_dst"] == -8.0


def test_parse_noaa_dst_empty_raises():
    """Empty DST payload raises UpdateFailed."""
    with pytest.raises(UpdateFailed):
        _parse_noaa_dst([])


def test_parse_noaa_dst_non_dict_entry_raises():
    """DST parse raises UpdateFailed when last entry is not a dict."""
    with pytest.raises(UpdateFailed):
        _parse_noaa_dst([{"dst": -10}, "bad_entry"])


def test_parse_noaa_dst_not_list_raises():
    """Non-list DST payload raises UpdateFailed."""
    with pytest.raises(UpdateFailed):
        _parse_noaa_dst({"dst": -5})


# ---------------------------------------------------------------------------
# Integration test: kp_forecast + dst fields flow through coordinator
# ---------------------------------------------------------------------------

KP_FORECAST_PAYLOAD = json.dumps(
    [
        {
            "time_tag": "2026-05-01 18:00:00",
            "kp": 3.0,
            "observed": "observed",
            "noaa_scale": None,
        },
        {
            "time_tag": "2026-05-01 21:00:00",
            "kp": 2.67,
            "observed": "predicted",
            "noaa_scale": None,
        },
    ]
)

DST_PAYLOAD = json.dumps(
    [
        {"time_tag": "2026-05-01 16:00:00", "dst": -16},
        {"time_tag": "2026-05-01 19:00:00", "dst": -8},
    ]
)


async def test_kp_forecast_dst_fields_in_coordinator(hass):
    """KP forecast and Dst fields flow through _async_update_data correctly."""
    coordinator = SolarCoordinator(hass, _make_entry(hass))

    async def mock_fetch(url: str) -> str:
        if "noaa-planetary-k-index-forecast" in url:
            return KP_FORECAST_PAYLOAD
        if "kyoto-dst" in url:
            return DST_PAYLOAD
        if "plasma-2-hour" in url:
            return PLASMA_PAYLOAD
        if "mag-2-hour" in url:
            return MAG_PAYLOAD
        if "swpc.noaa.gov" in url:
            return NOAA_PAYLOAD
        if "hamqsl.com" in url:
            return HAMQSL_PAYLOAD
        raise ValueError(f"Unexpected URL: {url}")

    with patch.object(coordinator, "_fetch_text", side_effect=mock_fetch):
        data = await coordinator._async_update_data()

    assert data["solar_kp_forecast"] == 2.67
    assert data["solar_dst"] == -8.0


# ---------------------------------------------------------------------------
# Predicted A-index / SFI parse unit tests
# ---------------------------------------------------------------------------


def test_parse_noaa_predicted_a_returns_all_three_days():
    """Predicted A-index parse returns 1-day, 2-day, and 3-day forecasts."""
    entries = [
        {"date": "2026-05-01", "afred_1_day": 9, "afred_2_day": 11, "afred_3_day": 7},
        {"date": "2026-04-30", "afred_1_day": 5, "afred_2_day": 8, "afred_3_day": 6},
    ]
    result = _parse_noaa_predicted_a(entries)
    assert result["solar_a_index_predicted"] == 9.0
    assert result["solar_a_index_predicted_2d"] == 11.0
    assert result["solar_a_index_predicted_3d"] == 7.0


def test_parse_noaa_predicted_a_uses_first_entry():
    """Predicted A-index parse uses first entry (most recent date)."""
    entries = [
        {"date": "2026-05-02", "afred_1_day": 20, "afred_2_day": 18, "afred_3_day": 15},
        {"date": "2026-05-01", "afred_1_day": 9, "afred_2_day": 11, "afred_3_day": 7},
    ]
    result = _parse_noaa_predicted_a(entries)
    assert result["solar_a_index_predicted"] == 20.0


def test_parse_noaa_predicted_a_empty_raises():
    """Empty predicted A-index payload raises UpdateFailed."""
    with pytest.raises(UpdateFailed):
        _parse_noaa_predicted_a([])


def test_parse_noaa_predicted_a_null_values_return_none():
    """Predicted A-index parse returns None for null forecast values."""
    entries = [
        {
            "date": "2026-05-01",
            "afred_1_day": None,
            "afred_2_day": None,
            "afred_3_day": None,
        }
    ]
    result = _parse_noaa_predicted_a(entries)
    assert result["solar_a_index_predicted"] is None
    assert result["solar_a_index_predicted_2d"] is None
    assert result["solar_a_index_predicted_3d"] is None


def test_parse_noaa_predicted_sfi_returns_one_day():
    """Predicted SFI parse returns the 1-day forecast from first entry."""
    entries = [
        {"date": "2026-05-01", "tencmfcst_1_day": 135},
        {"date": "2026-04-30", "tencmfcst_1_day": 130},
    ]
    result = _parse_noaa_predicted_sfi(entries)
    assert result["solar_flux_predicted"] == 135.0


def test_parse_noaa_predicted_sfi_empty_raises():
    """Empty predicted SFI payload raises UpdateFailed."""
    with pytest.raises(UpdateFailed):
        _parse_noaa_predicted_sfi([])


def test_parse_noaa_predicted_sfi_null_value_returns_none():
    """Predicted SFI parse returns None when forecast value is null."""
    entries = [{"date": "2026-05-01", "tencmfcst_1_day": None}]
    result = _parse_noaa_predicted_sfi(entries)
    assert result["solar_flux_predicted"] is None


# ---------------------------------------------------------------------------
# Integration test: predicted A-index + SFI fields flow through coordinator
# ---------------------------------------------------------------------------

PREDICTED_A_PAYLOAD = json.dumps(
    [
        {"date": "2026-05-01", "afred_1_day": 9, "afred_2_day": 11, "afred_3_day": 7},
        {"date": "2026-04-30", "afred_1_day": 5, "afred_2_day": 8, "afred_3_day": 6},
    ]
)

PREDICTED_SFI_PAYLOAD = json.dumps(
    [
        {"date": "2026-05-01", "tencmfcst_1_day": 135},
        {"date": "2026-04-30", "tencmfcst_1_day": 130},
    ]
)


async def test_predicted_index_fields_in_coordinator(hass):
    """Predicted A-index and SFI fields flow through _async_update_data correctly."""
    coordinator = SolarCoordinator(hass, _make_entry(hass))

    async def mock_fetch(url: str) -> str:
        if "predicted_fredericksburg_a_index" in url:
            return PREDICTED_A_PAYLOAD
        if "predicted_f107cm_flux" in url:
            return PREDICTED_SFI_PAYLOAD
        if "plasma-2-hour" in url:
            return PLASMA_PAYLOAD
        if "mag-2-hour" in url:
            return MAG_PAYLOAD
        if "noaa-planetary-k-index-forecast" in url:
            return KP_FORECAST_PAYLOAD
        if "kyoto-dst" in url:
            return DST_PAYLOAD
        if "swpc.noaa.gov" in url:
            return NOAA_PAYLOAD
        if "hamqsl.com" in url:
            return HAMQSL_PAYLOAD
        raise ValueError(f"Unexpected URL: {url}")

    with patch.object(coordinator, "_fetch_text", side_effect=mock_fetch):
        data = await coordinator._async_update_data()

    assert data["solar_a_index_predicted"] == 9.0
    assert data["solar_a_index_predicted_2d"] == 11.0
    assert data["solar_a_index_predicted_3d"] == 7.0
    assert data["solar_flux_predicted"] == 135.0


# ---------------------------------------------------------------------------
# Solar regions parse unit tests
# ---------------------------------------------------------------------------


def test_parse_noaa_solar_regions_counts_latest_date():
    """Solar regions parse counts entries matching the first (most recent) observed_date."""
    entries = [
        {"observed_date": "2026-05-01", "region": 13849},
        {"observed_date": "2026-05-01", "region": 13850},
        {"observed_date": "2026-05-01", "region": 13851},
        {"observed_date": "2026-04-30", "region": 13848},
        {"observed_date": "2026-04-29", "region": 13847},
    ]
    result = _parse_noaa_solar_regions(entries)
    assert result["solar_active_regions"] == 3


def test_parse_noaa_solar_regions_single_entry():
    """Solar regions parse works when there is only one active region."""
    entries = [{"observed_date": "2026-05-01", "region": 13849}]
    result = _parse_noaa_solar_regions(entries)
    assert result["solar_active_regions"] == 1


def test_parse_noaa_solar_regions_all_same_date():
    """Solar regions parse counts all entries when all share the same date."""
    entries = [
        {"observed_date": "2026-05-01", "region": 13849},
        {"observed_date": "2026-05-01", "region": 13850},
    ]
    result = _parse_noaa_solar_regions(entries)
    assert result["solar_active_regions"] == 2


def test_parse_noaa_solar_regions_empty_raises():
    """Empty solar regions payload raises UpdateFailed."""
    with pytest.raises(UpdateFailed):
        _parse_noaa_solar_regions([])


def test_parse_noaa_solar_regions_not_list_raises():
    """Non-list solar regions payload raises UpdateFailed."""
    with pytest.raises(UpdateFailed):
        _parse_noaa_solar_regions({"region": 13849})


# ---------------------------------------------------------------------------
# Integration tests: solar regions flow through coordinator
# ---------------------------------------------------------------------------

SOLAR_REGIONS_PAYLOAD = json.dumps(
    [
        {
            "observed_date": "2026-05-01",
            "region": 13849,
            "latitude": 12,
            "longitude": 45,
        },
        {
            "observed_date": "2026-05-01",
            "region": 13850,
            "latitude": -5,
            "longitude": 120,
        },
        {
            "observed_date": "2026-05-01",
            "region": 13851,
            "latitude": 20,
            "longitude": 200,
        },
        {
            "observed_date": "2026-04-30",
            "region": 13848,
            "latitude": 8,
            "longitude": 300,
        },
    ]
)


async def test_solar_regions_field_in_coordinator(hass):
    """Solar active regions field flows through _async_update_data in slow cycle."""
    coordinator = SolarCoordinator(hass, _make_entry(hass))

    async def mock_fetch(url: str) -> str:
        if "solar_regions" in url:
            return SOLAR_REGIONS_PAYLOAD
        if "predicted_fredericksburg_a_index" in url:
            return PREDICTED_A_PAYLOAD
        if "predicted_f107cm_flux" in url:
            return PREDICTED_SFI_PAYLOAD
        if "plasma-2-hour" in url:
            return PLASMA_PAYLOAD
        if "mag-2-hour" in url:
            return MAG_PAYLOAD
        if "noaa-planetary-k-index-forecast" in url:
            return KP_FORECAST_PAYLOAD
        if "kyoto-dst" in url:
            return DST_PAYLOAD
        if "swpc.noaa.gov" in url:
            return NOAA_PAYLOAD
        if "hamqsl.com" in url:
            return HAMQSL_PAYLOAD
        raise ValueError(f"Unexpected URL: {url}")

    with patch.object(coordinator, "_fetch_text", side_effect=mock_fetch):
        data = await coordinator._async_update_data()

    assert data["solar_active_regions"] == 3


async def test_solar_regions_not_fetched_outside_slow_cycle(hass):
    """Solar regions is NOT fetched when slow cycle is not due."""
    coordinator = SolarCoordinator(hass, _make_entry(hass))
    coordinator._last_slow_update = dt_util.utcnow()  # just ran

    async def track_fetch(url: str) -> str:
        if "solar_regions" in url:
            pytest.fail(
                f"solar_regions should not be fetched when slow cycle is not due: {url}"
            )
        if "swpc.noaa.gov" in url:
            return NOAA_PAYLOAD
        if "hamqsl.com" in url:
            return HAMQSL_PAYLOAD
        raise ValueError(f"Unexpected URL: {url}")

    with patch.object(coordinator, "_fetch_text", side_effect=track_fetch):
        await coordinator._async_update_data()
