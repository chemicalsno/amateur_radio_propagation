"""Diagnostics support for Amateur Radio Propagation."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import STATION_CODE, STATION_NAME, USER_STATION_CODE
from .types import HamRadioConfigEntry

_TO_REDACT = {STATION_CODE, STATION_NAME, USER_STATION_CODE}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: HamRadioConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data  # type: ignore[attr-defined]
    return {
        "entry_data": async_redact_data(dict(entry.data), _TO_REDACT),
        "coordinator_data": coordinator.data or {},
        "last_update_success": coordinator.last_update_success,
        "last_exception": str(coordinator.last_exception)
        if coordinator.last_exception
        else None,
    }
