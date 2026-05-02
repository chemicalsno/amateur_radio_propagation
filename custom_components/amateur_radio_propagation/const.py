"""Constants for the Amateur Radio Propagation integration."""

from __future__ import annotations

from datetime import timedelta
from enum import StrEnum
from typing import Final

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, Platform

# ---------------------------------------------------------------------------
# Domain
# ---------------------------------------------------------------------------
DOMAIN: Final = "amateur_radio_propagation"
PLATFORMS: Final = [Platform.SENSOR]
MANUFACTURER: Final = "hamqsl.com and kc2g.com"
MODEL: Final = "Amateur Radio Propagation"
VERSION: Final = "2.0.0"
CONFIGURATION_URL: Final = (
    "https://github.com/chemicalsno/amateur_radio_propagation#readme"
)
ENTITY_SOLAR_TITLE: Final = "Solar Data"

# ---------------------------------------------------------------------------
# Config entry data keys
# ---------------------------------------------------------------------------
CHOICE: Final = "choice"
STATION_CODE: Final = "station_code"
STATION_NAME: Final = "station_name"
USER_STATION_CODE: Final = "user_muf_station_code"
DASHBOARD_NOTIFIED: Final = "dashboard_notified"

# ---------------------------------------------------------------------------
# Config entry options keys
# ---------------------------------------------------------------------------
OPTION_STALE_HOURS: Final = "stale_hours"
OPTION_STALE_HOURS_DEFAULT: Final = 3


class Choice(StrEnum):
    """Integration operating mode."""

    SOLAR = "solar"
    MUF = "muf"


# ---------------------------------------------------------------------------
# External API URLs
# ---------------------------------------------------------------------------
URL_NOAA_XRAY: Final = (
    "https://services.swpc.noaa.gov/json/goes/primary/xray-flares-latest.json"
)
URL_NOAA_SCALES: Final = "https://services.swpc.noaa.gov/products/noaa-scales.json"
URL_NOAA_PROBABILITIES: Final = (
    "https://services.swpc.noaa.gov/json/solar_probabilities.json"
)
URL_NOAA_KP_1M: Final = "https://services.swpc.noaa.gov/json/planetary_k_index_1m.json"
URL_NOAA_ALERTS: Final = "https://services.swpc.noaa.gov/products/alerts.json"
URL_NOAA_PLASMA: Final = (
    "https://services.swpc.noaa.gov/products/solar-wind/plasma-2-hour.json"
)
URL_NOAA_MAG: Final = (
    "https://services.swpc.noaa.gov/products/solar-wind/mag-2-hour.json"
)
URL_NOAA_KP_FORECAST: Final = (
    "https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json"
)
URL_NOAA_DST: Final = "https://services.swpc.noaa.gov/products/kyoto-dst.json"
URL_NOAA_PREDICTED_A: Final = (
    "https://services.swpc.noaa.gov/json/predicted_fredericksburg_a_index.json"
)
URL_NOAA_PREDICTED_SFI: Final = (
    "https://services.swpc.noaa.gov/json/predicted_f107cm_flux.json"
)
URL_NOAA_SOLAR_REGIONS: Final = "https://services.swpc.noaa.gov/json/solar_regions.json"
URL_HAMQSL_XML: Final = "https://www.hamqsl.com/solarxml.php"
URL_KC2G_STATIONS: Final = "https://prop.kc2g.com/api/stations.json"

# ---------------------------------------------------------------------------
# Attribution strings
# ---------------------------------------------------------------------------
ATTRIBUTION_SOLAR: Final = (
    "Data provided by NOAA SWPC (services.swpc.noaa.gov) and hamqsl.com"
)
ATTRIBUTION_MUF: Final = (
    "Data provided by the kc2g.com ionosonde network (prop.kc2g.com)"
)

# ---------------------------------------------------------------------------
# Update intervals
# ---------------------------------------------------------------------------
POLL_INTERVAL_NOAA: Final = timedelta(minutes=15)
POLL_INTERVAL_HAMQSL: Final = timedelta(hours=3)
POLL_INTERVAL_MUF: Final = timedelta(minutes=30)
KC2G_STALE_THRESHOLD: Final = timedelta(hours=3)
REQUEST_TIMEOUT: Final = 10  # seconds — NOAA/hamqsl respond in <1s normally

# ---------------------------------------------------------------------------
# Solar sensor descriptions
# ---------------------------------------------------------------------------
SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    # --- Core ---
    SensorEntityDescription(
        key="solar_flux_index",
        translation_key="solar_flux_index",
        name="Solar Flux Index",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        key="solar_sunspots",
        translation_key="solar_sunspots",
        name="Solar Sunspots",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        key="solar_a_index",
        translation_key="solar_a_index",
        name="Solar A-Index",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        key="solar_k_index",
        translation_key="solar_k_index",
        name="Solar K-Index",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="solar_bz",
        translation_key="solar_bz",
        name="Solar Bz (hamqsl)",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="solar_wind",
        translation_key="solar_wind",
        name="Solar Wind (hamqsl)",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="km/s",
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        key="solar_hf_80_40_day",
        translation_key="solar_hf_80_40_day",
        name="HF Conditions 80m-40m Day",
    ),
    SensorEntityDescription(
        key="solar_hf_30_20_day",
        translation_key="solar_hf_30_20_day",
        name="HF Conditions 30m-20m Day",
    ),
    SensorEntityDescription(
        key="solar_hf_17_15_day",
        translation_key="solar_hf_17_15_day",
        name="HF Conditions 17m-15m Day",
    ),
    SensorEntityDescription(
        key="solar_hf_12_10_day",
        translation_key="solar_hf_12_10_day",
        name="HF Conditions 12m-10m Day",
    ),
    SensorEntityDescription(
        key="solar_hf_80_40_night",
        translation_key="solar_hf_80_40_night",
        name="HF Conditions 80m-40m Night",
    ),
    SensorEntityDescription(
        key="solar_hf_30_20_night",
        translation_key="solar_hf_30_20_night",
        name="HF Conditions 30m-20m Night",
    ),
    SensorEntityDescription(
        key="solar_hf_17_15_night",
        translation_key="solar_hf_17_15_night",
        name="HF Conditions 17m-15m Night",
    ),
    SensorEntityDescription(
        key="solar_hf_12_10_night",
        translation_key="solar_hf_12_10_night",
        name="HF Conditions 12m-10m Night",
    ),
    SensorEntityDescription(
        key="solar_geomag_field",
        translation_key="solar_geomag_field",
        name="HF Conditions Geomag Field",
    ),
    SensorEntityDescription(
        key="solar_sig_noise_lvl",
        translation_key="solar_sig_noise_lvl",
        name="HF Conditions Noise Level",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        key="solar_fof2",
        translation_key="solar_fof2",
        name="Solar foF2",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="MHz",
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="solar_xray",
        translation_key="solar_xray",
        name="Solar X-Ray Class",
    ),
    SensorEntityDescription(
        key="solar_xray_scale",
        translation_key="solar_xray_scale",
        name="Solar X-Ray Scale",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    # --- Bucket A/B: enabled by default ---
    SensorEntityDescription(
        key="solar_geomag_storm",
        translation_key="solar_geomag_storm",
        name="Geomagnetic Storm Scale",
    ),
    SensorEntityDescription(
        key="solar_radiation_storm",
        translation_key="solar_radiation_storm",
        name="Solar Radiation Storm Scale",
    ),
    SensorEntityDescription(
        key="solar_radio_blackout",
        translation_key="solar_radio_blackout",
        name="Radio Blackout Scale",
    ),
    SensorEntityDescription(
        key="solar_kp_estimated",
        translation_key="solar_kp_estimated",
        name="Estimated Kp (Fractional)",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        key="solar_flare_prob_m1",
        translation_key="solar_flare_prob_m1",
        name="M-Class Flare Probability (1-day)",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        key="solar_flare_prob_x1",
        translation_key="solar_flare_prob_x1",
        name="X-Class Flare Probability (1-day)",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        key="solar_pca",
        translation_key="solar_pca",
        name="Polar Cap Absorption",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        key="solar_alert_count",
        translation_key="solar_alert_count",
        name="Space Weather Alerts",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        key="solar_xray_peak_class",
        translation_key="solar_xray_peak_class",
        name="Solar X-Ray Peak Class",
    ),
    SensorEntityDescription(
        key="solar_vhf_aurora",
        translation_key="solar_vhf_aurora",
        name="VHF Aurora (Northern Hemisphere)",
    ),
    SensorEntityDescription(
        key="solar_vhf_eskip_eu",
        translation_key="solar_vhf_eskip_eu",
        name="VHF E-Skip Europe",
    ),
    SensorEntityDescription(
        key="solar_vhf_eskip_na",
        translation_key="solar_vhf_eskip_na",
        name="VHF E-Skip North America",
    ),
    SensorEntityDescription(
        key="solar_vhf_eskip_eu_6m",
        translation_key="solar_vhf_eskip_eu_6m",
        name="VHF E-Skip Europe 6m",
    ),
    SensorEntityDescription(
        key="solar_vhf_eskip_eu_4m",
        translation_key="solar_vhf_eskip_eu_4m",
        name="VHF E-Skip Europe 4m",
    ),
    SensorEntityDescription(
        key="solar_aurora_activity",
        translation_key="solar_aurora_activity",
        name="Aurora Activity",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        key="solar_aurora_latitude",
        translation_key="solar_aurora_latitude",
        name="Aurora Latitude",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="°",
        suggested_display_precision=1,
    ),
    # --- Bucket C: disabled by default ---
    SensorEntityDescription(
        key="solar_proton_flux",
        translation_key="solar_proton_flux",
        name="Solar Proton Flux",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="solar_electron_flux",
        translation_key="solar_electron_flux",
        name="Solar Electron Flux",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="solar_helium_line",
        translation_key="solar_helium_line",
        name="Solar Helium Line",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="solar_k_index_nighttime",
        translation_key="solar_k_index_nighttime",
        name="Solar K-Index (Nighttime)",
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="solar_xray_begin_class",
        translation_key="solar_xray_begin_class",
        name="Solar X-Ray Flare Begin Class",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="solar_xray_end_class",
        translation_key="solar_xray_end_class",
        name="Solar X-Ray Flare End Class",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="solar_xray_current_ratio",
        translation_key="solar_xray_current_ratio",
        name="Solar X-Ray Current Ratio",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="solar_flare_prob_m3",
        translation_key="solar_flare_prob_m3",
        name="M-Class Flare Probability (3-day)",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        key="solar_flare_prob_x3",
        translation_key="solar_flare_prob_x3",
        name="X-Class Flare Probability (3-day)",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    # --- New NOAA real-time and forecast sensors ---
    SensorEntityDescription(
        key="solar_wind_density",
        translation_key="solar_wind_density",
        name="Solar Wind Density",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="p/cc",
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="solar_wind_speed_noaa",
        translation_key="solar_wind_speed_noaa",
        name="Solar Wind Speed (NOAA)",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="km/s",
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        key="solar_bz_noaa",
        translation_key="solar_bz_noaa",
        name="Interplanetary Magnetic Field Bz (NOAA)",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="nT",
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="solar_wind_bt",
        translation_key="solar_wind_bt",
        name="Interplanetary Magnetic Field Bt",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="nT",
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key="solar_kp_forecast",
        translation_key="solar_kp_forecast",
        name="Kp Forecast (Next 3 Hours)",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        key="solar_dst",
        translation_key="solar_dst",
        name="Disturbance Storm Time Index (Dst)",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="nT",
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        key="solar_a_index_predicted",
        translation_key="solar_a_index_predicted",
        name="Predicted A-Index (1-Day)",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        key="solar_a_index_predicted_2d",
        translation_key="solar_a_index_predicted_2d",
        name="Predicted A-Index (2-Day)",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        key="solar_a_index_predicted_3d",
        translation_key="solar_a_index_predicted_3d",
        name="Predicted A-Index (3-Day)",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        key="solar_flux_predicted",
        translation_key="solar_flux_predicted",
        name="Predicted Solar Flux Index (1-Day)",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        key="solar_active_regions",
        translation_key="solar_active_regions",
        name="Active Solar Regions",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
)
