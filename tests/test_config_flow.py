"""Tests for the Amateur Radio Propagation config flow."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.amateur_radio_propagation.const import (
    CHOICE,
    DOMAIN,
    STATION_CODE,
    USER_STATION_CODE,
    Choice,
)
from custom_components.amateur_radio_propagation.config_flow import (
    CannotConnect,
    async_station_list_kc2g,
)

STATION_LIST = ["Boulder [BC840]", "Pruhonice [PQ052]"]


class _Response:
    def __init__(self, body: str, status: int = 200) -> None:
        self.status = status
        self._body = body

    async def text(self) -> str:
        return self._body


class _Session:
    def __init__(self, response: _Response) -> None:
        self._response = response

    async def get(self, url: str) -> _Response:
        return self._response


async def test_solar_entry_created(hass):
    """Choosing Solar creates a config entry with Choice.SOLAR."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CHOICE: Choice.SOLAR},
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CHOICE] == Choice.SOLAR


async def test_second_solar_entry_skips_to_station(hass):
    """When a Solar entry exists, the flow skips to station selection."""
    existing = MockConfigEntry(
        domain=DOMAIN,
        data={CHOICE: Choice.SOLAR},
        title="Solar Data",
        unique_id="Solar Data",
    )
    existing.add_to_hass(hass)

    with patch(
        "custom_components.amateur_radio_propagation.config_flow.async_station_list_kc2g",
        return_value=STATION_LIST,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )

    assert result["step_id"] == "station"


async def test_muf_entry_created(hass):
    """Choosing MUF and selecting a station creates a MUF config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    # Submitting MUF choice immediately calls async_step_station which fetches
    # the station list — the mock must be active for that configure call.
    with patch(
        "custom_components.amateur_radio_propagation.config_flow.async_station_list_kc2g",
        return_value=STATION_LIST,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CHOICE: Choice.MUF},
        )
        assert result["step_id"] == "station"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={USER_STATION_CODE: "Boulder [BC840]"},
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CHOICE] == Choice.MUF
    assert result["data"][STATION_CODE] == "BC840"


async def test_duplicate_muf_station_aborts(hass):
    """Selecting an already-configured MUF station aborts the flow."""
    existing = MockConfigEntry(
        domain=DOMAIN,
        data={CHOICE: Choice.MUF, STATION_CODE: "BC840"},
        title="Boulder",
        unique_id="legacy-bc840",
    )
    existing.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with patch(
        "custom_components.amateur_radio_propagation.config_flow.async_station_list_kc2g",
        return_value=STATION_LIST,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CHOICE: Choice.MUF},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={USER_STATION_CODE: "Boulder [BC840]"},
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_muf_invalid_station_selection_stays_on_form(hass):
    """Malformed station labels are rejected instead of being sliced into data."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    malformed_station_list = ["Boulder BC840"]

    with patch(
        "custom_components.amateur_radio_propagation.config_flow.async_station_list_kc2g",
        return_value=malformed_station_list,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CHOICE: Choice.MUF},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={USER_STATION_CODE: malformed_station_list[0]},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "station"
    assert result["errors"] == {"base": "invalid_station"}


async def test_muf_reconfigure_changes_station(hass):
    """Reconfiguring a MUF entry lets the user pick a different station."""
    from custom_components.amateur_radio_propagation.const import STATION_NAME

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CHOICE: Choice.MUF,
            USER_STATION_CODE: "Boulder [BC840]",
            STATION_CODE: "BC840",
            STATION_NAME: "Boulder",
        },
        title="Boulder",
        unique_id="Boulder [BC840]",
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.amateur_radio_propagation.config_flow.async_station_list_kc2g",
            return_value=STATION_LIST,
        ),
        patch(
            "custom_components.amateur_radio_propagation.coordinator_muf."
            "MufCoordinator._async_update_data",
            return_value={"solar_hf_muf_PQ052": 14.0},
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "reconfigure", "entry_id": entry.entry_id},
        )
        assert result["step_id"] == "reconfigure"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={USER_STATION_CODE: "Pruhonice [PQ052]"},
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[STATION_CODE] == "PQ052"


async def test_muf_reconfigure_to_existing_station_aborts(hass):
    """Reconfiguring to another entry's station aborts cleanly."""
    from custom_components.amateur_radio_propagation.const import STATION_NAME

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CHOICE: Choice.MUF,
            USER_STATION_CODE: "Boulder [BC840]",
            STATION_CODE: "BC840",
            STATION_NAME: "Boulder",
        },
        title="Boulder",
        unique_id="Boulder [BC840]",
    )
    duplicate = MockConfigEntry(
        domain=DOMAIN,
        data={
            CHOICE: Choice.MUF,
            USER_STATION_CODE: "Pruhonice [PQ052]",
            STATION_CODE: "PQ052",
            STATION_NAME: "Pruhonice",
        },
        title="Pruhonice",
        unique_id="Pruhonice [PQ052]",
    )
    entry.add_to_hass(hass)
    duplicate.add_to_hass(hass)

    with patch(
        "custom_components.amateur_radio_propagation.config_flow.async_station_list_kc2g",
        return_value=STATION_LIST,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "reconfigure", "entry_id": entry.entry_id},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={USER_STATION_CODE: "Pruhonice [PQ052]"},
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data[STATION_CODE] == "BC840"


async def test_solar_reconfigure_aborts(hass):
    """Reconfiguring a Solar entry immediately aborts (nothing to change)."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CHOICE: Choice.SOLAR},
        title="Solar Data",
        unique_id="Solar Data",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "reconfigure", "entry_id": entry.entry_id},
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_not_supported"


async def test_muf_cannot_connect_aborts(hass):
    """CannotConnect during station fetch aborts the flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    # CannotConnect is raised inside async_step_station, which is called
    # when the MUF choice is submitted — patch must cover that configure call.
    with patch(
        "custom_components.amateur_radio_propagation.config_flow.async_station_list_kc2g",
        side_effect=CannotConnect,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CHOICE: Choice.MUF},
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"


async def test_station_list_non_list_json_raises_cannot_connect(
    hass: HomeAssistant,
) -> None:
    """Station list parser rejects valid JSON with the wrong top-level shape."""
    with patch(
        "custom_components.amateur_radio_propagation.config_flow.async_get_clientsession",
        return_value=_Session(_Response(json.dumps({"stations": []}))),
    ):
        with pytest.raises(CannotConnect):
            await async_station_list_kc2g(hass)


async def test_station_list_sorted_by_distance(hass: HomeAssistant) -> None:
    """Station list is sorted nearest-first using HA latitude and longitude."""
    hass.config.latitude = 40.0
    hass.config.longitude = -105.0
    payload = json.dumps(
        [
            {
                "station": {
                    "code": "FAR",
                    "name": "Far",
                    "latitude": 0.0,
                    "longitude": 0.0,
                }
            },
            {
                "station": {
                    "code": "NEAR",
                    "name": "Near",
                    "latitude": 40.1,
                    "longitude": 255.0,
                }
            },
        ]
    )

    with patch(
        "custom_components.amateur_radio_propagation.config_flow.async_get_clientsession",
        return_value=_Session(_Response(payload)),
    ):
        stations = await async_station_list_kc2g(hass)

    assert stations == ["Near [NEAR]", "Far [FAR]"]
