"""Dashboard setup notification for MUF config entries."""

from __future__ import annotations

import pathlib

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant

from .const import DASHBOARD_NOTIFIED, STATION_CODE, STATION_NAME
from .types import HamRadioConfigEntry

_DASHBOARDS_DIR = pathlib.Path(__file__).parent / "dashboards"

_CURATED_TEMPLATES: tuple[tuple[str, str, str], ...] = (
    ("MUF Station", "muf-station-dashboard.yaml", "None"),
    ("Vanilla", "vanilla-dashboard.yaml", "None"),
    (
        "Bubble Card",
        "bubble-card-dashboard.yaml",
        "`custom:bubble-card` (HACS → Frontend)",
    ),
    (
        "Mushroom Operator",
        "mushroom-operator-dashboard.yaml",
        "Mushroom cards (HACS → Frontend)",
    ),
    (
        "Mini Graph Trends",
        "mini-graph-trends-dashboard.yaml",
        "`custom:mini-graph-card` (HACS → Frontend)",
    ),
)


async def async_notify_dashboard_ready(
    hass: HomeAssistant, entry: HamRadioConfigEntry
) -> None:
    """Create a one-time persistent notification with pre-filled dashboard YAML.

    Fires once per MUF config entry. Skips silently if already fired.
    """
    if entry.data.get(DASHBOARD_NOTIFIED):
        return

    station_code: str = entry.data.get(STATION_CODE, "") or ""
    station_name: str = entry.data.get(STATION_NAME, station_code) or station_code
    notification_id = f"amateur_radio_propagation_dashboard_{entry.entry_id}"

    lines: list[str] = [
        f"## Your MUF dashboard is ready — station **{station_name} ({station_code})**",
        "",
        "Paste one of the YAML blocks below into your Lovelace dashboard via "
        "**Edit → Raw configuration editor**. "
        "Install any listed HACS dependencies first.",
        "",
    ]

    for name, filename, deps in _CURATED_TEMPLATES:
        try:
            # Small bundled package files — blocking read is negligible in practice.
            yaml_text = (_DASHBOARDS_DIR / filename).read_text(encoding="utf-8")
        except OSError:
            continue
        yaml_text = yaml_text.replace("IF843", station_code).replace(
            "if843", station_code.lower()
        )
        lines += [
            f"### {name}",
            f"**Dependencies:** {deps}",
            "",
            "```yaml",
            yaml_text.rstrip(),
            "```",
            "",
        ]

    persistent_notification.async_create(
        hass,
        message="\n".join(lines),
        title="Amateur Radio Propagation — Dashboard Setup",
        notification_id=notification_id,
    )

    hass.config_entries.async_update_entry(
        entry, data={**entry.data, DASHBOARD_NOTIFIED: True}
    )
