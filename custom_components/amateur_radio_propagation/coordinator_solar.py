"""SolarCoordinator: polls NOAA XRAY (15 min) and hamqsl XML (3 hr)."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from http import HTTPStatus
from typing import Any, cast
from defusedxml import ElementTree as ET
from xml.etree.ElementTree import Element

import aiohttp

from homeassistant.helpers.issue_registry import (
    IssueSeverity,
    async_create_issue,
    async_delete_issue,
)
from homeassistant.util import dt as dt_util
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    ATTRIBUTION_SOLAR,
    DOMAIN,
    POLL_INTERVAL_HAMQSL,
    POLL_INTERVAL_NOAA,
    REQUEST_TIMEOUT,
    URL_HAMQSL_XML,
    URL_NOAA_ALERTS,
    URL_NOAA_DST,
    URL_NOAA_KP_1M,
    URL_NOAA_KP_FORECAST,
    URL_NOAA_MAG,
    URL_NOAA_PLASMA,
    URL_NOAA_PREDICTED_A,
    URL_NOAA_PREDICTED_SFI,
    URL_NOAA_PROBABILITIES,
    URL_NOAA_SCALES,
    URL_NOAA_SOLAR_REGIONS,
    URL_NOAA_XRAY,
)
from .types import HamRadioConfigEntry

_LOGGER = logging.getLogger(__name__)

# Circuit breaker: open after this many consecutive failures, cool down for this long
_CIRCUIT_THRESHOLD: int = 3
_CIRCUIT_COOLDOWN: timedelta = timedelta(hours=1)

# Raise a repair issue if NOAA X-ray hasn't been successfully fetched in this long
_NOAA_STALE_THRESHOLD: timedelta = timedelta(hours=1)

# Exceptions that indicate a transient fetch problem (not a bug)
_FETCH_ERRORS = (
    aiohttp.ClientError,
    asyncio.TimeoutError,
    json.JSONDecodeError,
    IndexError,
    KeyError,
    ValueError,
    UpdateFailed,
)

_HAMQSL_SCALAR_KEYS: dict[str, str] = {
    "solarflux": "solar_flux_index",
    "sunspots": "solar_sunspots",
    "aindex": "solar_a_index",
    "kindex": "solar_k_index",
    "magneticfield": "solar_bz",
    "solarwind": "solar_wind",
    "fof2": "solar_fof2",
    "geomagfield": "solar_geomag_field",
    "signalnoise": "solar_sig_noise_lvl",
    "aurora": "solar_aurora_activity",
    "latdegree": "solar_aurora_latitude",
    "protonflux": "solar_proton_flux",
    "electonflux": "solar_electron_flux",  # upstream typo is canonical
    "heliumline": "solar_helium_line",
    "kindexnt": "solar_k_index_nighttime",
}

# Subset of _HAMQSL_SCALAR_KEYS whose values must be numeric.
# Non-parseable text (e.g. "No Report") is converted to None so that
# HamRadioSensor.available returns False instead of exposing a string state.
_HAMQSL_NUMERIC_KEYS: frozenset[str] = frozenset(
    {
        "solarflux",
        "sunspots",
        "aindex",
        "kindex",
        "magneticfield",
        "solarwind",
        "fof2",
        "aurora",
        "latdegree",
        "protonflux",
        "electonflux",
        "heliumline",
        "kindexnt",
    }
)

_HAMQSL_BAND_KEYS: dict[tuple[str, str], str] = {
    ("80m-40m", "day"): "solar_hf_80_40_day",
    ("80m-40m", "night"): "solar_hf_80_40_night",
    ("30m-20m", "day"): "solar_hf_30_20_day",
    ("30m-20m", "night"): "solar_hf_30_20_night",
    ("17m-15m", "day"): "solar_hf_17_15_day",
    ("17m-15m", "night"): "solar_hf_17_15_night",
    ("12m-10m", "day"): "solar_hf_12_10_day",
    ("12m-10m", "night"): "solar_hf_12_10_night",
}

_HAMQSL_VHF_KEYS: dict[tuple[str, str], str] = {
    ("vhf-aurora", "northern_hemi"): "solar_vhf_aurora",
    ("E-Skip", "europe"): "solar_vhf_eskip_eu",
    ("E-Skip", "north_america"): "solar_vhf_eskip_na",
    ("E-Skip", "europe_6m"): "solar_vhf_eskip_eu_6m",
    ("E-Skip", "europe_4m"): "solar_vhf_eskip_eu_4m",
}

_NOAA_EXTRA_KEYS: dict[str, str] = {
    "max_class": "solar_xray_peak_class",
    "begin_class": "solar_xray_begin_class",
    "end_class": "solar_xray_end_class",
    "current_ratio": "solar_xray_current_ratio",
}

_XRAY_SCALE: dict[str, int] = {"A": 1, "B": 10, "C": 100, "M": 1000, "X": 10000}


def _text(element: Element | None) -> str | None:
    """Return stripped text from an XML element, or None."""
    if element is None or element.text is None:
        return None
    return element.text.strip() or None


def _parse_noaa_xray(entries: Any) -> dict[str, Any]:
    """Parse the NOAA X-ray payload into coordinator data keys."""
    if not isinstance(entries, list) or not entries:
        raise UpdateFailed("NOAA X-ray payload did not return any entries")
    entry = entries[0]
    if not isinstance(entry, dict):
        raise UpdateFailed("NOAA X-ray entry is not an object")

    xray_class = entry.get("current_class")
    if not isinstance(xray_class, str) or not xray_class:
        raise UpdateFailed("NOAA X-ray entry is missing current_class")

    parsed: dict[str, Any] = {"solar_xray": xray_class}
    prefix = xray_class[:1]
    factor = _XRAY_SCALE.get(prefix, 0)
    try:
        parsed["solar_xray_scale"] = float(xray_class[1:]) * factor if factor else 0.0
    except ValueError:
        parsed["solar_xray_scale"] = 0.0
    for src_key, data_key in _NOAA_EXTRA_KEYS.items():
        parsed[data_key] = entry.get(src_key)
    return parsed


def _parse_noaa_scales(payload: Any) -> dict[str, Any]:
    """Parse the NOAA space weather scales payload into coordinator data keys."""
    if not isinstance(payload, dict):
        raise UpdateFailed("NOAA scales payload is not an object")
    current = payload.get("0")
    if not isinstance(current, dict):
        raise UpdateFailed("NOAA scales payload is missing current scales")

    parsed: dict[str, Any] = {}
    for source_key, data_key in (
        ("G", "solar_geomag_storm"),
        ("S", "solar_radiation_storm"),
        ("R", "solar_radio_blackout"),
    ):
        source_value = current.get(source_key)
        parsed[data_key] = (
            source_value.get("Scale") if isinstance(source_value, dict) else None
        )
    return parsed


def _parse_noaa_probabilities(entries: Any) -> dict[str, Any]:
    """Parse NOAA flare probabilities into coordinator data keys."""
    if not isinstance(entries, list) or not entries:
        raise UpdateFailed("NOAA probabilities payload did not return any entries")
    last = entries[-1]
    if not isinstance(last, dict):
        raise UpdateFailed("NOAA probabilities entry is not an object")
    return {
        "solar_flare_prob_m1": last.get("m_class_1_day"),
        "solar_flare_prob_x1": last.get("x_class_1_day"),
        "solar_flare_prob_m3": last.get("m_class_3_day"),
        "solar_flare_prob_x3": last.get("x_class_3_day"),
        "solar_pca": last.get("polar_cap_absorption"),
    }


def _parse_noaa_kp(entries: Any) -> dict[str, Any]:
    """Parse NOAA planetary K-index payload into coordinator data keys."""
    if not isinstance(entries, list) or not entries:
        raise UpdateFailed("NOAA K-index payload did not return any entries")
    last = entries[-1]
    if isinstance(last, list) and len(last) >= 3:
        return {"solar_kp_estimated": last[2]}
    if isinstance(last, dict):
        return {"solar_kp_estimated": last.get("estimated_kp")}
    raise UpdateFailed("NOAA K-index entry has an unsupported shape")


def _parse_noaa_alerts(entries: Any) -> dict[str, Any]:
    """Parse NOAA alert payload into coordinator data keys."""
    if not isinstance(entries, list):
        raise UpdateFailed("NOAA alerts payload is not a list")
    message = None
    if entries:
        first = entries[0]
        if not isinstance(first, dict):
            raise UpdateFailed("NOAA alert entry is not an object")
        message = first.get("message")
    return {
        "solar_alert_count": len(entries),
        "solar_alert_message": message,
    }


def _parse_noaa_plasma(entries: Any) -> dict[str, Any]:
    """Parse NOAA real-time solar wind plasma into coordinator data keys."""
    if not isinstance(entries, list) or len(entries) < 2:
        raise UpdateFailed("NOAA plasma payload is missing data rows")
    header = entries[0]
    if not isinstance(header, list) or not header or header[0] != "time_tag":
        raise UpdateFailed("NOAA plasma payload header row is unexpected")
    last = entries[-1]
    if not isinstance(last, list) or len(last) < 3:
        raise UpdateFailed("NOAA plasma data row has unexpected shape")
    try:
        density = float(last[1]) if last[1] is not None else None
        speed = float(last[2]) if last[2] is not None else None
    except (ValueError, TypeError):
        density = speed = None
    return {
        "solar_wind_density": density,
        "solar_wind_speed_noaa": speed,
    }


def _parse_noaa_mag(entries: Any) -> dict[str, Any]:
    """Parse NOAA real-time solar wind magnetometer into coordinator data keys."""
    if not isinstance(entries, list) or len(entries) < 2:
        raise UpdateFailed("NOAA mag payload is missing data rows")
    header = entries[0]
    if not isinstance(header, list) or not header or header[0] != "time_tag":
        raise UpdateFailed("NOAA mag payload header row is unexpected")
    last = entries[-1]
    if not isinstance(last, list) or len(last) < 7:
        raise UpdateFailed("NOAA mag data row has unexpected shape")
    try:
        bz_gsm = float(last[3]) if last[3] is not None else None
        bt = float(last[6]) if last[6] is not None else None
    except (ValueError, TypeError):
        bz_gsm = bt = None
    return {
        "solar_bz_noaa": bz_gsm,
        "solar_wind_bt": bt,
    }


def _parse_noaa_kp_forecast(entries: Any) -> dict[str, Any]:
    """Parse NOAA planetary Kp index forecast into coordinator data keys."""
    if not isinstance(entries, list) or not entries:
        raise UpdateFailed("NOAA KP forecast payload is empty")
    for entry in entries:
        if isinstance(entry, dict) and entry.get("observed") == "predicted":
            kp = entry.get("kp")
            return {"solar_kp_forecast": float(kp) if kp is not None else None}
    return {"solar_kp_forecast": None}


def _parse_noaa_dst(entries: Any) -> dict[str, Any]:
    """Parse Kyoto Dst index payload into coordinator data keys."""
    if not isinstance(entries, list) or not entries:
        raise UpdateFailed("NOAA DST payload is empty")
    last = entries[-1]
    if not isinstance(last, dict):
        raise UpdateFailed("NOAA DST entry is not an object")
    dst = last.get("dst")
    return {"solar_dst": float(dst) if dst is not None else None}


def _parse_noaa_predicted_a(entries: Any) -> dict[str, Any]:
    """Parse NOAA predicted A-index (Fredericksburg) into coordinator data keys."""
    if not isinstance(entries, list) or not entries:
        raise UpdateFailed("NOAA predicted A-index payload is empty")
    first = entries[0]
    if not isinstance(first, dict):
        raise UpdateFailed("NOAA predicted A-index entry is not an object")
    a1 = first.get("afred_1_day")
    a2 = first.get("afred_2_day")
    a3 = first.get("afred_3_day")
    return {
        "solar_a_index_predicted": float(a1) if a1 is not None else None,
        "solar_a_index_predicted_2d": float(a2) if a2 is not None else None,
        "solar_a_index_predicted_3d": float(a3) if a3 is not None else None,
    }


def _parse_noaa_predicted_sfi(entries: Any) -> dict[str, Any]:
    """Parse NOAA predicted 10.7cm solar flux into coordinator data keys."""
    if not isinstance(entries, list) or not entries:
        raise UpdateFailed("NOAA predicted SFI payload is empty")
    first = entries[0]
    if not isinstance(first, dict):
        raise UpdateFailed("NOAA predicted SFI entry is not an object")
    sfi = first.get("tencmfcst_1_day")
    return {"solar_flux_predicted": float(sfi) if sfi is not None else None}


def _parse_noaa_solar_regions(entries: Any) -> dict[str, Any]:
    """Parse NOAA solar regions list into coordinator data keys."""
    if not isinstance(entries, list) or not entries:
        raise UpdateFailed("NOAA solar regions payload is empty")
    first = entries[0]
    if not isinstance(first, dict):
        raise UpdateFailed("NOAA solar regions entry is not an object")
    observed_date = first.get("observed_date")
    count = sum(
        1
        for e in entries
        if isinstance(e, dict) and e.get("observed_date") == observed_date
    )
    return {"solar_active_regions": count}


def _parse_hamqsl(body: str) -> dict[str, Any]:
    """Parse hamqsl XML into coordinator data keys."""
    root = ET.fromstring(body)
    solardata = root.find("solardata")
    if solardata is None:
        raise UpdateFailed("hamqsl XML missing <solardata> element")

    parsed: dict[str, Any] = {}
    for xml_tag, data_key in _HAMQSL_SCALAR_KEYS.items():
        value = _text(solardata.find(xml_tag))
        if value is None:
            continue
        if xml_tag in _HAMQSL_NUMERIC_KEYS:
            try:
                parsed[data_key] = float(value)
            except ValueError:
                parsed[data_key] = None
        else:
            parsed[data_key] = value

    conditions = solardata.find("calculatedconditions")
    if conditions is not None:
        for band in conditions.findall("band"):
            key = (band.get("name") or "", band.get("time") or "")
            band_data_key = _HAMQSL_BAND_KEYS.get(key)
            value = _text(band)
            if band_data_key and value is not None:
                parsed[band_data_key] = value

    vhf = solardata.find("calculatedvhfconditions")
    if vhf is not None:
        for phenom in vhf.findall("phenomenon"):
            key = (phenom.get("name") or "", phenom.get("location") or "")
            vhf_data_key = _HAMQSL_VHF_KEYS.get(key)
            value = _text(phenom)
            if vhf_data_key and value is not None:
                parsed[vhf_data_key] = value

    return parsed


class SolarCoordinator(DataUpdateCoordinator[dict[str, Any]]):  # type: ignore[misc]
    """Coordinator for solar space-weather data."""

    attribution = ATTRIBUTION_SOLAR

    def __init__(self, hass: HomeAssistant, entry: HamRadioConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"amateur_radio_propagation solar ({entry.title})",
            update_interval=POLL_INTERVAL_NOAA,
        )
        self._session = async_get_clientsession(hass)
        self._last_slow_update: datetime | None = None
        self._started_at: datetime = dt_util.utcnow()

        # Freshness timestamps exposed to sensors via extra_state_attributes
        self.last_noaa_success: datetime | None = None
        self.last_hamqsl_success: datetime | None = None

        # Circuit breaker state per source name
        self._circuit_failures: dict[str, int] = {}
        self._circuit_open_until: dict[str, datetime] = {}
        self._source_available: dict[str, bool] = {}

    # ------------------------------------------------------------------
    # Main update
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict[str, Any]:
        data: dict[str, Any] = dict(self.data or {})
        now = dt_util.utcnow()
        slow_due = (
            self._last_slow_update is None
            or now >= self._last_slow_update + POLL_INTERVAL_HAMQSL
        )

        fast_sources = [
            ("NOAA X-ray", self._update_noaa),
            ("NOAA scales", self._update_noaa_scales),
            ("NOAA probabilities", self._update_noaa_probabilities),
            ("NOAA K-index", self._update_noaa_kp),
            ("NOAA alerts", self._update_noaa_alerts),
            ("NOAA plasma", self._update_noaa_plasma),
            ("NOAA mag", self._update_noaa_mag),
            ("NOAA KP forecast", self._update_noaa_kp_forecast),
            ("NOAA DST", self._update_noaa_dst),
            ("NOAA predicted A-index", self._update_noaa_predicted_a),
            ("NOAA predicted SFI", self._update_noaa_predicted_sfi),
        ]

        # Skip sources whose circuit breaker is open; run the rest in parallel
        active = [
            (n, fn) for n, fn in fast_sources if not self._circuit_is_open(n, now)
        ]
        skipped = [n for n, _ in fast_sources if self._circuit_is_open(n, now)]
        if skipped:
            _LOGGER.debug("Circuit open — skipping: %s", ", ".join(skipped))

        results = await asyncio.gather(
            *(fn(data) for _, fn in active),
            return_exceptions=True,
        )

        noaa_xray_ok = False
        for (name, _), result in zip(active, results):
            if isinstance(result, Exception):
                self._log_source_unavailable(name, result)
                self._circuit_record_failure(name, now)
            else:
                self._log_source_recovered(name)
                self._circuit_clear(name)
                if name == "NOAA X-ray":
                    noaa_xray_ok = True

        if noaa_xray_ok:
            self.last_noaa_success = now

        self._check_noaa_staleness(now)

        if slow_due:
            try:
                await self._update_hamqsl(data)
                self._last_slow_update = now
                self.last_hamqsl_success = now
            except (*_FETCH_ERRORS, ET.ParseError) as err:
                self._log_source_unavailable("hamqsl", err)
            else:
                self._log_source_recovered("hamqsl")

            try:
                await self._update_solar_regions(data)
            except _FETCH_ERRORS as err:
                self._log_source_unavailable("NOAA solar regions", err)
            else:
                self._log_source_recovered("NOAA solar regions")

        if not data:
            raise UpdateFailed("No solar data could be fetched from any source")

        return data

    # ------------------------------------------------------------------
    # Circuit breaker helpers
    # ------------------------------------------------------------------

    def _circuit_is_open(self, name: str, now: datetime) -> bool:
        """Return True if the circuit for this source is tripped."""
        until = self._circuit_open_until.get(name)
        if until is None:
            return False
        if now >= until:
            # Cooldown expired — reset so next call gets a fresh attempt
            del self._circuit_open_until[name]
            self._circuit_failures.pop(name, None)
            return False
        return True

    def _circuit_record_failure(self, name: str, now: datetime) -> None:
        """Record a failure; open the circuit after _CIRCUIT_THRESHOLD failures."""
        count = self._circuit_failures.get(name, 0) + 1
        self._circuit_failures[name] = count
        if count >= _CIRCUIT_THRESHOLD:
            open_until = now + _CIRCUIT_COOLDOWN
            self._circuit_open_until[name] = open_until
            _LOGGER.warning(
                "Circuit breaker opened for %s after %d failures — will retry at %s",
                name,
                count,
                open_until.isoformat(),
            )

    def _circuit_clear(self, name: str) -> None:
        """Reset circuit state on success."""
        self._circuit_failures.pop(name, None)
        self._circuit_open_until.pop(name, None)

    def _log_source_unavailable(self, name: str, err: Exception) -> None:
        """Log a source failure once until it recovers."""
        if self._source_available.get(name) is False:
            _LOGGER.debug("Solar update still skipping %s: %s", name, err)
            return
        self._source_available[name] = False
        _LOGGER.warning("Solar update skipping %s: %s", name, err)

    def _log_source_recovered(self, name: str) -> None:
        """Log once when a previously unavailable source recovers."""
        if self._source_available.get(name) is False:
            _LOGGER.info("Solar source recovered: %s", name)
        self._source_available[name] = True

    # ------------------------------------------------------------------
    # Repair issue for persistent NOAA failure
    # ------------------------------------------------------------------

    def _check_noaa_staleness(self, now: datetime) -> None:
        """Raise a repair issue if NOAA data has been unreachable too long."""
        reference = self.last_noaa_success or self._started_at
        if now >= reference + _NOAA_STALE_THRESHOLD:
            async_create_issue(
                self.hass,
                DOMAIN,
                "stale_noaa",
                is_fixable=False,
                severity=IssueSeverity.WARNING,
                translation_key="stale_noaa",
                translation_placeholders={
                    "url": "https://www.swpc.noaa.gov/",
                },
            )
        else:
            async_delete_issue(self.hass, DOMAIN, "stale_noaa")

    def dismiss_issue(self) -> None:
        """Clear the NOAA staleness repair issue on unload."""
        async_delete_issue(self.hass, DOMAIN, "stale_noaa")

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    async def _fetch_text(self, url: str) -> str:
        async with asyncio.timeout(REQUEST_TIMEOUT):
            req = await self._session.get(url)
            if req.status != HTTPStatus.OK:
                raise UpdateFailed(f"Request to {url} failed: HTTP {req.status}")
            return cast(str, await req.text())

    async def _fetch_json(self, url: str) -> Any:
        return json.loads(await self._fetch_text(url))

    # ------------------------------------------------------------------
    # Fast-cycle NOAA sources
    # ------------------------------------------------------------------

    async def _update_noaa(self, data: dict[str, Any]) -> None:
        entries = await self._fetch_json(URL_NOAA_XRAY)
        data.update(_parse_noaa_xray(entries))

    async def _update_noaa_scales(self, data: dict[str, Any]) -> None:
        payload = await self._fetch_json(URL_NOAA_SCALES)
        data.update(_parse_noaa_scales(payload))

    async def _update_noaa_probabilities(self, data: dict[str, Any]) -> None:
        entries = await self._fetch_json(URL_NOAA_PROBABILITIES)
        data.update(_parse_noaa_probabilities(entries))

    async def _update_noaa_kp(self, data: dict[str, Any]) -> None:
        entries = await self._fetch_json(URL_NOAA_KP_1M)
        data.update(_parse_noaa_kp(entries))

    async def _update_noaa_alerts(self, data: dict[str, Any]) -> None:
        entries = await self._fetch_json(URL_NOAA_ALERTS)
        data.update(_parse_noaa_alerts(entries))

    async def _update_noaa_plasma(self, data: dict[str, Any]) -> None:
        entries = await self._fetch_json(URL_NOAA_PLASMA)
        data.update(_parse_noaa_plasma(entries))

    async def _update_noaa_mag(self, data: dict[str, Any]) -> None:
        entries = await self._fetch_json(URL_NOAA_MAG)
        data.update(_parse_noaa_mag(entries))

    async def _update_noaa_kp_forecast(self, data: dict[str, Any]) -> None:
        entries = await self._fetch_json(URL_NOAA_KP_FORECAST)
        data.update(_parse_noaa_kp_forecast(entries))

    async def _update_noaa_dst(self, data: dict[str, Any]) -> None:
        entries = await self._fetch_json(URL_NOAA_DST)
        data.update(_parse_noaa_dst(entries))

    async def _update_noaa_predicted_a(self, data: dict[str, Any]) -> None:
        entries = await self._fetch_json(URL_NOAA_PREDICTED_A)
        data.update(_parse_noaa_predicted_a(entries))

    async def _update_noaa_predicted_sfi(self, data: dict[str, Any]) -> None:
        entries = await self._fetch_json(URL_NOAA_PREDICTED_SFI)
        data.update(_parse_noaa_predicted_sfi(entries))

    # ------------------------------------------------------------------
    # Slow-cycle hamqsl source
    # ------------------------------------------------------------------

    async def _update_hamqsl(self, data: dict[str, Any]) -> None:
        body = await self._fetch_text(URL_HAMQSL_XML)
        data.update(_parse_hamqsl(body))

    # ------------------------------------------------------------------
    # Slow-cycle NOAA sources (large or daily-update files)
    # ------------------------------------------------------------------

    async def _update_solar_regions(self, data: dict[str, Any]) -> None:
        entries = await self._fetch_json(URL_NOAA_SOLAR_REGIONS)
        data.update(_parse_noaa_solar_regions(entries))
