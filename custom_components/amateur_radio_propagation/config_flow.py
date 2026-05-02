"""Config flow for the Amateur Radio Propagation integration."""

from __future__ import annotations

import asyncio
import json
import logging
import math
import re
from http import HTTPStatus
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    FlowResult as ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import selector

from .const import (
    CHOICE,
    DOMAIN,
    ENTITY_SOLAR_TITLE,
    OPTION_STALE_HOURS,
    OPTION_STALE_HOURS_DEFAULT,
    REQUEST_TIMEOUT,
    STATION_CODE,
    STATION_NAME,
    USER_STATION_CODE,
    URL_KC2G_STATIONS,
    Choice,
)

_LOGGER = logging.getLogger(__name__)
_STATION_LABEL_RE = re.compile(r"^(.+?)\s+\[([^\[\]]+)\]$")


class CannotConnect(HomeAssistantError):  # type: ignore[misc]
    """Raised when the kc2g station list cannot be fetched."""


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two WGS-84 points."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


def _normalize_lon(lon: float) -> float:
    """Convert 0-360 longitude (kc2g convention) to -180..180."""
    return lon - 360 if lon > 180 else lon


def _parse_station_label(raw: str) -> tuple[str, str]:
    """Return station name and code from a station selector label."""
    match = _STATION_LABEL_RE.fullmatch(raw.strip())
    if match is None:
        raise ValueError("Invalid station selector label")

    station_name = match.group(1).replace(",", "").strip()
    station_code = match.group(2).strip()
    if not station_name or not station_code:
        raise ValueError("Invalid station selector label")
    return station_name, station_code


async def async_station_list_kc2g(hass: HomeAssistant) -> list[str]:
    """Fetch kc2g ionosonde stations, return display strings sorted by distance."""
    websession = async_get_clientsession(hass)
    try:
        async with asyncio.timeout(REQUEST_TIMEOUT):
            req = await websession.get(URL_KC2G_STATIONS)
    except (asyncio.TimeoutError, aiohttp.ClientError) as err:
        raise CannotConnect from err

    if req.status != HTTPStatus.OK:
        raise CannotConnect(f"HTTP {req.status}")

    try:
        entries = json.loads(await req.text())
    except json.JSONDecodeError as err:
        raise CannotConnect from err
    if not isinstance(entries, list):
        raise CannotConnect("kc2g station list did not return a list")

    user_lat = hass.config.latitude
    user_lon = hass.config.longitude
    stations: list[tuple[float, str]] = []

    for entry in entries:
        station = entry.get("station") if isinstance(entry, dict) else None
        if not isinstance(station, dict):
            continue
        code = station.get("code")
        name = station.get("name") or code
        if not code:
            continue
        try:
            lat = float(station["latitude"])
            lon = _normalize_lon(float(station["longitude"]))
            distance = _haversine(user_lat, user_lon, lat, lon)
        except (TypeError, ValueError, KeyError):
            distance = float("inf")
        stations.append((distance, f"{name} [{code}]"))

    stations.sort(key=lambda item: item[0])
    return [label for _, label in stations]


def _muf_station_configured(
    entries: list[ConfigEntry],
    station_code: str,
    ignored_entry_id: str | None = None,
) -> bool:
    """Return True if a MUF station is already configured."""
    return any(
        entry.entry_id != ignored_entry_id
        and entry.data.get(CHOICE) == Choice.MUF
        and entry.data.get(STATION_CODE) == station_code
        for entry in entries
    )


class HamRadioConfigFlow(ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg,misc]
    """Handle a config flow for Amateur Radio Propagation."""

    VERSION = 1

    @staticmethod
    @callback  # type: ignore[untyped-decorator]
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        return HamRadioOptionsFlow(config_entry)

    _choice: Choice | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Initial step: choose Solar or MUF."""
        solar_exists = any(
            e.data.get(CHOICE) == Choice.SOLAR for e in self._async_current_entries()
        )

        if solar_exists:
            # Solar already configured — go straight to station selection
            self._choice = Choice.MUF
            return await self.async_step_station()

        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {vol.Required(CHOICE, default=Choice.SOLAR): vol.In(list(Choice))}  # type: ignore[call-arg]
                ),
            )

        self._choice = Choice(user_input[CHOICE])
        if self._choice == Choice.MUF:
            return await self.async_step_station()

        # Solar
        await self.async_set_unique_id(ENTITY_SOLAR_TITLE)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=ENTITY_SOLAR_TITLE,
            data={CHOICE: Choice.SOLAR},
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Allow a MUF entry to change its station."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if entry is None or entry.data.get(CHOICE) != Choice.MUF:
            return self.async_abort(reason="reconfigure_not_supported")

        if user_input is not None:
            raw = str(user_input[USER_STATION_CODE])
            try:
                station_name, station_code = _parse_station_label(raw)
            except ValueError:
                station_list = await async_station_list_kc2g(self.hass)
                return self.async_show_form(
                    step_id="reconfigure",
                    data_schema=vol.Schema(
                        {
                            vol.Required(USER_STATION_CODE): selector(
                                {
                                    "select": {
                                        "options": station_list,
                                        "mode": "dropdown",
                                    }
                                }
                            )
                        }
                    ),
                    errors={"base": "invalid_station"},
                )
            if _muf_station_configured(
                self._async_current_entries(),
                station_code,
                ignored_entry_id=entry.entry_id,
            ):
                return self.async_abort(reason="already_configured")
            return self.async_update_reload_and_abort(
                entry,
                title=station_name,
                data={
                    **entry.data,
                    USER_STATION_CODE: raw,
                    STATION_CODE: station_code,
                    STATION_NAME: station_name,
                },
                reason="reconfigure_successful",
            )

        try:
            station_list = await async_station_list_kc2g(self.hass)
        except CannotConnect:
            return self.async_abort(reason="cannot_connect")

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(USER_STATION_CODE): selector(
                        {"select": {"options": station_list, "mode": "dropdown"}}
                    )
                }
            ),
        )

    async def async_step_station(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2: pick an ionosonde station."""
        if user_input is not None:
            raw = str(user_input[USER_STATION_CODE])
            try:
                station_name, station_code = _parse_station_label(raw)
            except ValueError:
                station_list = await async_station_list_kc2g(self.hass)
                return self.async_show_form(
                    step_id="station",
                    data_schema=vol.Schema(
                        {
                            vol.Required(USER_STATION_CODE): selector(
                                {
                                    "select": {
                                        "options": station_list,
                                        "mode": "dropdown",
                                    }
                                }
                            )
                        }
                    ),
                    errors={"base": "invalid_station"},
                )
            if _muf_station_configured(self._async_current_entries(), station_code):
                return self.async_abort(reason="already_configured")
            await self.async_set_unique_id(raw)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=station_name,
                data={
                    CHOICE: Choice.MUF,
                    USER_STATION_CODE: raw,
                    STATION_CODE: station_code,
                    STATION_NAME: station_name,
                },
            )

        try:
            station_list = await async_station_list_kc2g(self.hass)
        except CannotConnect:
            return self.async_abort(reason="cannot_connect")

        return self.async_show_form(
            step_id="station",
            data_schema=vol.Schema(
                {
                    vol.Required(USER_STATION_CODE): selector(
                        {"select": {"options": station_list, "mode": "dropdown"}}
                    )
                }
            ),
        )


class HamRadioOptionsFlow(OptionsFlow):  # type: ignore[misc]
    """Options flow for Amateur Radio Propagation (MUF entries only)."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage MUF options. Solar entries have no configurable options."""
        if self._entry.data.get(CHOICE) != Choice.MUF:
            return self.async_abort(reason="no_options")

        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current_hours = self._entry.options.get(
            OPTION_STALE_HOURS, OPTION_STALE_HOURS_DEFAULT
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(OPTION_STALE_HOURS, default=current_hours): selector(
                        {
                            "select": {
                                "options": [
                                    {"value": 1, "label": "1 hour"},
                                    {"value": 2, "label": "2 hours"},
                                    {"value": 3, "label": "3 hours"},
                                    {"value": 6, "label": "6 hours"},
                                    {"value": 12, "label": "12 hours"},
                                    {"value": 24, "label": "24 hours"},
                                ],
                                "mode": "dropdown",
                            }
                        }
                    )
                }
            ),
        )
