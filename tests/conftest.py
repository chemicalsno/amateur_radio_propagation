"""Shared pytest fixtures."""

from __future__ import annotations

from unittest.mock import patch

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading of custom integrations in every test."""
    yield


@pytest.fixture(autouse=True)
def mock_coordinator_clientsessions():
    """Avoid creating Home Assistant's aiohttp resolver in tests."""
    with (
        patch(
            "custom_components.amateur_radio_propagation.coordinator_solar."
            "async_get_clientsession",
            return_value=object(),
        ),
        patch(
            "custom_components.amateur_radio_propagation.coordinator_muf."
            "async_get_clientsession",
            return_value=object(),
        ),
    ):
        yield
