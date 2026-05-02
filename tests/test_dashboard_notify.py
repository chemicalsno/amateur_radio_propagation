"""Tests for dashboard_notify."""

from __future__ import annotations

from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.amateur_radio_propagation.const import (
    CHOICE,
    DASHBOARD_NOTIFIED,
    DOMAIN,
    STATION_CODE,
    STATION_NAME,
    Choice,
)
from custom_components.amateur_radio_propagation.dashboard_notify import (
    _CURATED_TEMPLATES,
    async_notify_dashboard_ready,
)


def _muf_entry(**extra_data: object) -> MockConfigEntry:
    data = {
        CHOICE: Choice.MUF,
        STATION_CODE: "BC840",
        STATION_NAME: "Boulder",
        **extra_data,
    }
    return MockConfigEntry(domain=DOMAIN, data=data, title="Boulder", unique_id="BC840")


async def test_notification_created_on_first_muf_setup(hass, tmp_path):
    """Persistent notification is created on first call for a fresh MUF entry."""
    entry = _muf_entry()
    entry.add_to_hass(hass)

    for _, filename, _ in _CURATED_TEMPLATES:
        (tmp_path / filename).write_text(f"title: {filename}\nviews: []\n")

    with (
        patch(
            "custom_components.amateur_radio_propagation.dashboard_notify._DASHBOARDS_DIR",
            tmp_path,
        ),
        patch(
            "homeassistant.components.persistent_notification.async_create"
        ) as mock_create,
    ):
        await async_notify_dashboard_ready(hass, entry)

    mock_create.assert_called_once()
    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["notification_id"] == (
        f"amateur_radio_propagation_dashboard_{entry.entry_id}"
    )
    assert call_kwargs["title"] == "Amateur Radio Propagation — Dashboard Setup"


async def test_notification_skipped_if_already_notified(hass):
    """No notification fired when dashboard_notified flag is already True."""
    entry = _muf_entry(**{DASHBOARD_NOTIFIED: True})
    entry.add_to_hass(hass)

    with patch(
        "homeassistant.components.persistent_notification.async_create"
    ) as mock_create:
        await async_notify_dashboard_ready(hass, entry)

    mock_create.assert_not_called()


async def test_station_code_substituted_in_notification(hass, tmp_path):
    """IF843/if843 placeholders are replaced with the actual station code."""
    entry = _muf_entry()
    entry.add_to_hass(hass)

    for _, filename, _ in _CURATED_TEMPLATES:
        (tmp_path / filename).write_text(
            "entity: sensor.amateur_radio_propagation_solar_hf_muf_IF843\nentity2: solar_hf_muf_if843\n"
        )

    with (
        patch(
            "custom_components.amateur_radio_propagation.dashboard_notify._DASHBOARDS_DIR",
            tmp_path,
        ),
        patch(
            "homeassistant.components.persistent_notification.async_create"
        ) as mock_create,
    ):
        await async_notify_dashboard_ready(hass, entry)

    message = mock_create.call_args.kwargs["message"]
    assert "BC840" in message
    assert "bc840" in message
    assert "IF843" not in message
    assert "if843" not in message


async def test_station_name_shown_in_notification(hass, tmp_path):
    """Notification header includes station name and code."""
    entry = _muf_entry()
    entry.add_to_hass(hass)

    for _, filename, _ in _CURATED_TEMPLATES:
        (tmp_path / filename).write_text("title: Test\nviews: []\n")

    with (
        patch(
            "custom_components.amateur_radio_propagation.dashboard_notify._DASHBOARDS_DIR",
            tmp_path,
        ),
        patch(
            "homeassistant.components.persistent_notification.async_create"
        ) as mock_create,
    ):
        await async_notify_dashboard_ready(hass, entry)

    message = mock_create.call_args.kwargs["message"]
    assert "Boulder" in message
    assert "BC840" in message


async def test_dashboard_notified_flag_persisted(hass, tmp_path):
    """entry.data is updated with dashboard_notified=True after notification fires."""
    entry = _muf_entry()
    entry.add_to_hass(hass)

    for _, filename, _ in _CURATED_TEMPLATES:
        (tmp_path / filename).write_text("title: Test\nviews: []\n")

    with (
        patch(
            "custom_components.amateur_radio_propagation.dashboard_notify._DASHBOARDS_DIR",
            tmp_path,
        ),
        patch("homeassistant.components.persistent_notification.async_create"),
    ):
        await async_notify_dashboard_ready(hass, entry)

    assert entry.data.get(DASHBOARD_NOTIFIED) is True


async def test_missing_template_file_skipped_gracefully(hass, tmp_path):
    """A missing template file is skipped; remaining templates still appear."""
    entry = _muf_entry()
    entry.add_to_hass(hass)

    # Write only the first template; leave others absent
    first_filename = _CURATED_TEMPLATES[0][1]
    (tmp_path / first_filename).write_text("title: Only One\nviews: []\n")

    with (
        patch(
            "custom_components.amateur_radio_propagation.dashboard_notify._DASHBOARDS_DIR",
            tmp_path,
        ),
        patch(
            "homeassistant.components.persistent_notification.async_create"
        ) as mock_create,
    ):
        await async_notify_dashboard_ready(hass, entry)

    # Notification still fires (just with fewer templates)
    mock_create.assert_called_once()
