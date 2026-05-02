"""MufCoordinator: polls kc2g ionosonde station data every 30 minutes."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from http import HTTPStatus
from typing import Any, cast

import aiohttp

from homeassistant.helpers.issue_registry import (
    IssueSeverity,
    async_create_issue,
    async_delete_issue,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    ATTRIBUTION_MUF,
    CONFIGURATION_URL,
    DOMAIN,
    KC2G_STALE_THRESHOLD,
    OPTION_STALE_HOURS,
    OPTION_STALE_HOURS_DEFAULT,
    POLL_INTERVAL_MUF,
    REQUEST_TIMEOUT,
    STATION_CODE,
    URL_KC2G_STATIONS,
)
from .types import HamRadioConfigEntry

_LOGGER = logging.getLogger(__name__)

# (kc2g field name, data key suffix)
# mufd → muf preserves legacy entity IDs from v1
_KC2G_STATION_FIELDS: tuple[tuple[str, str], ...] = (
    ("mufd", "muf"),
    ("fof2", "fof2"),
    ("foe", "foe"),
    ("cs", "cs"),
    ("foes", "foes"),
    ("hmf2", "hmf2"),
    ("tec", "tec"),
    ("hme", "hme"),
    ("md", "md"),
    ("fof1", "fof1"),
    ("hmf1", "hmf1"),
    ("scalef2", "scalef2"),
    ("yf2", "yf2"),
)


def _parse_kc2g_station(entries: Any, station_code: str) -> dict[str, Any]:
    """Return the kc2g record for the configured station."""
    if not isinstance(entries, list):
        raise UpdateFailed("kc2g stations.json did not return a list")

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        station = entry.get("station")
        if isinstance(station, dict) and station.get("code") == station_code:
            return entry

    raise UpdateFailed(f"kc2g station {station_code!r} not found in feed")


class MufCoordinator(DataUpdateCoordinator[dict[str, Any]]):  # type: ignore[misc]
    """Coordinator for ionosonde MUF data from a single kc2g station."""

    attribution = ATTRIBUTION_MUF

    def __init__(self, hass: HomeAssistant, entry: HamRadioConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"amateur_radio_propagation muf ({entry.title})",
            update_interval=POLL_INTERVAL_MUF,
        )
        self._session = async_get_clientsession(hass)
        self._entry = entry
        self.station_code: str = entry.data.get(STATION_CODE, "") or ""
        self.last_kc2g_success: datetime | None = None
        self._kc2g_available = True

    async def _async_update_data(self) -> dict[str, Any]:
        data: dict[str, Any] = dict(self.data or {})
        try:
            await self._update_kc2g(data)
            self.last_kc2g_success = dt_util.utcnow()
            self._log_kc2g_recovered()
        except (
            aiohttp.ClientError,
            asyncio.TimeoutError,
            json.JSONDecodeError,
            IndexError,
            KeyError,
            ValueError,
            UpdateFailed,
        ) as err:
            if not data:
                raise UpdateFailed(f"Error fetching MUF data: {err}") from err
            self._log_kc2g_unavailable(err)
        return data

    def _log_kc2g_unavailable(self, err: Exception) -> None:
        """Log kc2g failure once until it recovers."""
        if not self._kc2g_available:
            _LOGGER.debug("MUF update still failing, keeping previous data: %s", err)
            return
        self._kc2g_available = False
        _LOGGER.warning("MUF update failed, keeping previous data: %s", err)

    def _log_kc2g_recovered(self) -> None:
        """Log once when kc2g recovers after a failure."""
        if not self._kc2g_available:
            _LOGGER.info("MUF source recovered: kc2g")
        self._kc2g_available = True

    async def _fetch_text(self, url: str) -> str:
        async with asyncio.timeout(REQUEST_TIMEOUT):
            req = await self._session.get(url)
            if req.status != HTTPStatus.OK:
                raise UpdateFailed(f"Request to {url} failed: HTTP {req.status}")
            return cast(str, await req.text())

    async def _update_kc2g(self, data: dict[str, Any]) -> None:
        entries = json.loads(await self._fetch_text(URL_KC2G_STATIONS))
        station_code = self.station_code
        record = _parse_kc2g_station(entries, station_code)

        for field, suffix in _KC2G_STATION_FIELDS:
            data[f"solar_hf_{suffix}_{station_code}"] = record.get(field)

        stale_hours = self._entry.options.get(
            OPTION_STALE_HOURS, OPTION_STALE_HOURS_DEFAULT
        )
        issue_id = f"stale_{station_code}"
        if _kc2g_is_stale(record, timedelta(hours=stale_hours)):
            station_name = record.get("station", {}).get("name", station_code)
            last_time = record.get("time", "unknown")
            async_create_issue(
                self.hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                severity=IssueSeverity.WARNING,
                translation_key="stale_station_data",
                translation_placeholders={
                    "station_name": station_name,
                    "station_code": station_code,
                    "last_time": str(last_time),
                    "url": CONFIGURATION_URL,
                },
            )
        else:
            async_delete_issue(self.hass, DOMAIN, issue_id)

    def dismiss_issue(self) -> None:
        """Delete the staleness repair issue for this station on unload."""
        async_delete_issue(self.hass, DOMAIN, f"stale_{self.station_code}")


def _kc2g_is_stale(
    record: dict[str, Any], threshold: timedelta = KC2G_STALE_THRESHOLD
) -> bool:
    """Return True if station data is older than threshold."""
    raw_time = record.get("time")
    if not isinstance(raw_time, str):
        return False
    try:
        parsed = dt_util.parse_datetime(raw_time)
    except (ValueError, TypeError):
        return False
    if parsed is None:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt_util.UTC)
    return cast(bool, dt_util.utcnow() - parsed > threshold)
