"""Types for the Amateur Radio Propagation integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeAlias

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

if TYPE_CHECKING:
    HamRadioConfigEntry: TypeAlias = ConfigEntry[DataUpdateCoordinator[dict[str, Any]]]  # type: ignore[type-arg]
else:
    HamRadioConfigEntry: TypeAlias = ConfigEntry
