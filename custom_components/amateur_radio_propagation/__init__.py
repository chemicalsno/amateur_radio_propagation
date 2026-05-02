"""Amateur Radio Propagation integration."""

from __future__ import annotations

import logging
from typing import cast

from homeassistant.core import HomeAssistant

from .const import CHOICE, PLATFORMS, Choice
from .coordinator_muf import MufCoordinator
from .coordinator_solar import SolarCoordinator
from .dashboard_notify import async_notify_dashboard_ready
from .types import HamRadioConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: HamRadioConfigEntry) -> bool:
    """Set up a config entry."""
    choice = entry.data[CHOICE]

    if choice == Choice.SOLAR:
        coordinator = SolarCoordinator(hass, entry)
    elif choice == Choice.MUF:
        coordinator = MufCoordinator(hass, entry)
    else:
        _LOGGER.error("Unknown integration choice: %s", choice)
        return False

    # Raises ConfigEntryNotReady on first-fetch failure → HA retries automatically
    await coordinator.async_config_entry_first_refresh()

    # Clean up staleness repair issues when the entry is unloaded
    entry.async_on_unload(coordinator.dismiss_issue)

    # Reload the entry when options change (e.g. stale threshold)
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_options_change))

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if choice == Choice.MUF:
        await async_notify_dashboard_ready(hass, entry)

    return True


async def _async_reload_on_options_change(
    hass: HomeAssistant, entry: HamRadioConfigEntry
) -> None:
    """Reload the entry when its options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: HamRadioConfigEntry) -> bool:
    """Unload a config entry."""
    return cast(
        bool, await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    )
