"""Sensor platform for the Amateur Radio Propagation integration."""

from __future__ import annotations

import logging
from typing import Any, cast

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.util import slugify

from .const import (
    CHOICE,
    CONFIGURATION_URL,
    DOMAIN,
    MANUFACTURER,
    MODEL,
    SENSOR_TYPES,
    STATION_CODE,
    VERSION,
    Choice,
)
from .types import HamRadioConfigEntry

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


def _muf_descriptions(station_code: str) -> tuple[SensorEntityDescription, ...]:
    """Return sensor descriptions for a configured MUF station."""
    return (
        # --- Always enabled ---
        SensorEntityDescription(
            key=f"solar_hf_muf_{station_code}",
            translation_key="hf_muf",
            name="Solar HF MUF",
            device_class=SensorDeviceClass.FREQUENCY,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="MHz",
            suggested_display_precision=1,
        ),
        SensorEntityDescription(
            key=f"solar_hf_fof2_{station_code}",
            translation_key="hf_fof2",
            name="Solar HF foF2",
            device_class=SensorDeviceClass.FREQUENCY,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="MHz",
            suggested_display_precision=1,
        ),
        SensorEntityDescription(
            key=f"solar_hf_foe_{station_code}",
            translation_key="hf_foe",
            name="Solar HF foE",
            device_class=SensorDeviceClass.FREQUENCY,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="MHz",
            suggested_display_precision=1,
        ),
        SensorEntityDescription(
            key=f"solar_hf_cs_{station_code}",
            translation_key="hf_cs",
            name="Solar HF Confidence",
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=0,
        ),
        # --- Bucket A/B: enabled by default ---
        SensorEntityDescription(
            key=f"solar_hf_foes_{station_code}",
            translation_key="hf_foes",
            name="Solar HF foEs (Sporadic E)",
            device_class=SensorDeviceClass.FREQUENCY,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="MHz",
            suggested_display_precision=1,
        ),
        SensorEntityDescription(
            key=f"solar_hf_hmf2_{station_code}",
            translation_key="hf_hmf2",
            name="Solar HF hmF2",
            device_class=SensorDeviceClass.DISTANCE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="km",
            suggested_display_precision=0,
        ),
        SensorEntityDescription(
            key=f"solar_hf_tec_{station_code}",
            translation_key="hf_tec",
            name="Solar HF TEC",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="TECU",
            suggested_display_precision=1,
        ),
        # --- Bucket C: disabled by default ---
        SensorEntityDescription(
            key=f"solar_hf_hme_{station_code}",
            translation_key="hf_hme",
            name="Solar HF hmE",
            device_class=SensorDeviceClass.DISTANCE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="km",
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
        ),
        SensorEntityDescription(
            key=f"solar_hf_md_{station_code}",
            translation_key="hf_md",
            name="Solar HF M(3000)F2",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        SensorEntityDescription(
            key=f"solar_hf_fof1_{station_code}",
            translation_key="hf_fof1",
            name="Solar HF foF1",
            device_class=SensorDeviceClass.FREQUENCY,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="MHz",
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
        ),
        SensorEntityDescription(
            key=f"solar_hf_hmf1_{station_code}",
            translation_key="hf_hmf1",
            name="Solar HF hmF1",
            device_class=SensorDeviceClass.DISTANCE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="km",
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
        ),
        SensorEntityDescription(
            key=f"solar_hf_scalef2_{station_code}",
            translation_key="hf_scalef2",
            name="Solar HF Scale Height F2",
            device_class=SensorDeviceClass.DISTANCE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="km",
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
        ),
        SensorEntityDescription(
            key=f"solar_hf_yf2_{station_code}",
            translation_key="hf_yf2",
            name="Solar HF yF2",
            device_class=SensorDeviceClass.DISTANCE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="km",
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
        ),
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HamRadioConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry."""
    coordinator = entry.runtime_data  # type: ignore[attr-defined]
    choice: str = entry.data[CHOICE]

    if choice == Choice.SOLAR:
        descriptions: tuple[SensorEntityDescription, ...] = SENSOR_TYPES
    elif choice == Choice.MUF:
        station_code = entry.data.get(STATION_CODE, "") or ""
        descriptions = _muf_descriptions(station_code)
    else:
        _LOGGER.error("Unknown integration choice: %s", choice)
        return

    async_add_entities(
        HamRadioSensor(coordinator, entry, description) for description in descriptions
    )


class HamRadioSensor(
    CoordinatorEntity[DataUpdateCoordinator[dict[str, Any]]],  # type: ignore[misc]
    SensorEntity,  # type: ignore[misc]
):
    """A sensor entity backed by coordinator data."""

    _attr_has_entity_name = True
    should_poll: bool = False  # type: ignore[override]  # resolve CoordinatorEntity / SensorEntity MRO conflict

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, Any]],
        entry: HamRadioConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        slug = slugify(description.key.replace("/", "_"))
        self.entity_id = f"sensor.{DOMAIN}_{slug}"
        self._attr_unique_id = f"{entry.entry_id}_{slug}"
        self._attr_device_info = DeviceInfo(
            name=entry.title,
            identifiers={(DOMAIN, entry.entry_id)},
            configuration_url=CONFIGURATION_URL,
            entry_type=DeviceEntryType.SERVICE,
            manufacturer=MANUFACTURER,
            model=MODEL,
            sw_version=VERSION,
        )

    @property
    def native_value(self) -> Any:
        return (self.coordinator.data or {}).get(self.entity_description.key)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {}
        attribution = getattr(self.coordinator, "attribution", None)
        if attribution:
            attrs[ATTR_ATTRIBUTION] = attribution
        # Freshness: expose when each upstream source was last successfully fetched
        last_noaa = getattr(self.coordinator, "last_noaa_success", None)
        if last_noaa:
            attrs["source_updated_noaa"] = last_noaa.isoformat()
        last_hamqsl = getattr(self.coordinator, "last_hamqsl_success", None)
        if last_hamqsl:
            attrs["source_updated_hamqsl"] = last_hamqsl.isoformat()
        last_kc2g = getattr(self.coordinator, "last_kc2g_success", None)
        if last_kc2g:
            attrs["source_updated_kc2g"] = last_kc2g.isoformat()
        if self.entity_description.key == "solar_alert_count":
            message = (self.coordinator.data or {}).get("solar_alert_message")
            if message:
                attrs["latest_alert"] = message
        return attrs

    @property
    def available(self) -> bool:
        return cast(bool, super().available and self.native_value is not None)

    @callback  # type: ignore[untyped-decorator]
    def _handle_coordinator_update(self) -> None:
        super()._handle_coordinator_update()
