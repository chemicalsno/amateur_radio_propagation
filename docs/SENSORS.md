# Sensor Reference

This page lists the entities exposed by the Amateur Radio Propagation integration. Entity IDs are generated from the integration domain and sensor key, for example `sensor.amateur_radio_propagation_solar_flux_index`.

## Solar Data

Solar Data is global and supports one config entry.

### Core Solar Indices

Source: hamqsl.com unless noted.

| Sensor | Key | Unit | Description |
|--------|-----|------|-------------|
| Solar Flux Index | `solar_flux_index` | sfu | 10.7 cm radio flux, a primary indicator of solar activity. |
| Solar Sunspots | `solar_sunspots` | count | Daily sunspot count. |
| Solar A-Index | `solar_a_index` | index | Daily geomagnetic activity index. |
| Solar K-Index | `solar_k_index` | index | 3-hour geomagnetic activity index. |
| Solar Bz (hamqsl) | `solar_bz` | nT | Interplanetary magnetic field Bz from hamqsl. |
| Solar Wind (hamqsl) | `solar_wind` | km/s | Solar wind speed from hamqsl. |
| Solar foF2 | `solar_fof2` | MHz | F2 layer critical frequency from hamqsl. |

### HF Band Conditions

Source: hamqsl.com. Values are typically `Good`, `Fair`, or `Poor`.

| Sensor | Key | Description |
|--------|-----|-------------|
| HF Conditions 80m-40m Day | `solar_hf_80_40_day` | Daytime 80m and 40m outlook. |
| HF Conditions 30m-20m Day | `solar_hf_30_20_day` | Daytime 30m and 20m outlook. |
| HF Conditions 17m-15m Day | `solar_hf_17_15_day` | Daytime 17m and 15m outlook. |
| HF Conditions 12m-10m Day | `solar_hf_12_10_day` | Daytime 12m and 10m outlook. |
| HF Conditions 80m-40m Night | `solar_hf_80_40_night` | Nighttime 80m and 40m outlook. |
| HF Conditions 30m-20m Night | `solar_hf_30_20_night` | Nighttime 30m and 20m outlook. |
| HF Conditions 17m-15m Night | `solar_hf_17_15_night` | Nighttime 17m and 15m outlook. |
| HF Conditions 12m-10m Night | `solar_hf_12_10_night` | Nighttime 12m and 10m outlook. |
| HF Conditions Geomag Field | `solar_geomag_field` | Qualitative geomagnetic field state. |
| HF Conditions Noise Level | `solar_sig_noise_lvl` | Signal-to-noise level indicator. |

### NOAA Space Weather

Source: NOAA SWPC.

| Sensor | Key | Unit | Description |
|--------|-----|------|-------------|
| Solar X-Ray Class | `solar_xray` | class | Current GOES X-ray class. |
| Solar X-Ray Scale | `solar_xray_scale` | numeric | Numeric X-ray scale derived from the current class. |
| Solar X-Ray Peak Class | `solar_xray_peak_class` | class | Peak class from the latest flare event. |
| Geomagnetic Storm Scale | `solar_geomag_storm` | G scale | Current NOAA G-scale. |
| Solar Radiation Storm Scale | `solar_radiation_storm` | S scale | Current NOAA S-scale. |
| Radio Blackout Scale | `solar_radio_blackout` | R scale | Current NOAA R-scale. |
| Estimated Kp (Fractional) | `solar_kp_estimated` | index | Real-time fractional Kp. |
| M-Class Flare Probability (1-day) | `solar_flare_prob_m1` | % | Probability of at least one M-class flare today. |
| X-Class Flare Probability (1-day) | `solar_flare_prob_x1` | % | Probability of at least one X-class flare today. |
| M-Class Flare Probability (3-day) | `solar_flare_prob_m3` | % | 3-day M-class flare outlook. |
| X-Class Flare Probability (3-day) | `solar_flare_prob_x3` | % | 3-day X-class flare outlook. |
| Polar Cap Absorption | `solar_pca` | % | Probability of polar cap radio absorption. |
| Space Weather Alerts | `solar_alert_count` | count | Count of active NOAA alerts, with latest alert details in attributes. |
| Solar Wind Speed (NOAA) | `solar_wind_speed_noaa` | km/s | Real-time NOAA solar wind speed. |
| Interplanetary Magnetic Field Bz (NOAA) | `solar_bz_noaa` | nT | Real-time NOAA IMF Bz. |
| Kp Forecast (Next 3 Hours) | `solar_kp_forecast` | index | NOAA forecast Kp for the upcoming 3-hour window. |
| Disturbance Storm Time Index (Dst) | `solar_dst` | nT | Ring current strength; negative values indicate geomagnetic storms. |
| Predicted A-Index (1-Day) | `solar_a_index_predicted` | index | NOAA predicted A-index for today. |
| Predicted A-Index (2-Day) | `solar_a_index_predicted_2d` | index | NOAA predicted A-index for tomorrow. |
| Predicted A-Index (3-Day) | `solar_a_index_predicted_3d` | index | NOAA predicted A-index for the day after tomorrow. |
| Predicted Solar Flux Index (1-Day) | `solar_flux_predicted` | sfu | NOAA predicted 10.7 cm solar flux for today. |
| Active Solar Regions | `solar_active_regions` | count | Count of numbered active solar regions. |

### VHF And Aurora

Source: hamqsl.com.

| Sensor | Key | Unit | Description |
|--------|-----|------|-------------|
| VHF Aurora (Northern Hemisphere) | `solar_vhf_aurora` | text | Aurora-enhanced VHF propagation likelihood. |
| VHF E-Skip Europe | `solar_vhf_eskip_eu` | text | Sporadic-E VHF outlook for Europe. |
| VHF E-Skip North America | `solar_vhf_eskip_na` | text | Sporadic-E VHF outlook for North America. |
| VHF E-Skip Europe 6m | `solar_vhf_eskip_eu_6m` | text | Sporadic-E outlook for 6m in Europe. |
| VHF E-Skip Europe 4m | `solar_vhf_eskip_eu_4m` | text | Sporadic-E outlook for 4m in Europe. |
| Aurora Activity | `solar_aurora_activity` | 0-100 | Aurora activity level. |
| Aurora Latitude | `solar_aurora_latitude` | degrees | Equatorward boundary of visible aurora. |

### Solar Diagnostics

These entities are disabled by default. Enable them individually from the entity list.

| Sensor | Key | Unit | Description |
|--------|-----|------|-------------|
| Solar Proton Flux | `solar_proton_flux` | pfu | Energetic proton flux. |
| Solar Electron Flux | `solar_electron_flux` | pfu | Energetic electron flux. |
| Solar Helium Line | `solar_helium_line` | flux | Solar helium 10830 Angstrom line flux. |
| Solar K-Index (Nighttime) | `solar_k_index_nighttime` | index | Nighttime K-index fallback from hamqsl. |
| Solar X-Ray Flare Begin Class | `solar_xray_begin_class` | class | X-ray class at flare onset. |
| Solar X-Ray Flare End Class | `solar_xray_end_class` | class | X-ray class at flare end. |
| Solar X-Ray Current Ratio | `solar_xray_current_ratio` | ratio | Ratio of current X-ray flux to background level. |
| Solar Wind Density | `solar_wind_density` | p/cc | Raw NOAA solar wind proton density. |
| Interplanetary Magnetic Field Bt | `solar_wind_bt` | nT | NOAA IMF total field magnitude. |

## MUF Station

MUF Station entries are per ionosonde station. Entity keys include the configured station code, for example `solar_hf_muf_IF843`.

### Enabled By Default

| Sensor | Key pattern | Unit | Description |
|--------|-------------|------|-------------|
| MUF | `solar_hf_muf_<station>` | MHz | Maximum usable frequency for F2 propagation at 3000 km path. |
| foF2 | `solar_hf_fof2_<station>` | MHz | F2 layer critical frequency. |
| foE | `solar_hf_foe_<station>` | MHz | E layer critical frequency. |
| Confidence Score | `solar_hf_cs_<station>` | score | Data reliability score reported by the ionosonde. |
| foEs | `solar_hf_foes_<station>` | MHz | Sporadic-E critical frequency. |
| hmF2 | `solar_hf_hmf2_<station>` | km | Virtual height of the F2 layer peak. |
| TEC | `solar_hf_tec_<station>` | TECU | Total electron content. Some stations may not publish this field. |
| M(3000)F2 | `solar_hf_md_<station>` | ratio | Propagation factor used to derive MUF from foF2. |

### Diagnostics

These entities are disabled by default.

| Sensor | Key pattern | Unit | Description |
|--------|-------------|------|-------------|
| hmE | `solar_hf_hme_<station>` | km | Virtual height of E layer peak. |
| foF1 | `solar_hf_fof1_<station>` | MHz | F1 layer critical frequency. |
| hmF1 | `solar_hf_hmf1_<station>` | km | Virtual height of F1 layer peak. |
| Scale Height F2 | `solar_hf_scalef2_<station>` | km | F2 layer scale height. |
| yF2 | `solar_hf_yf2_<station>` | km | F2 layer half-thickness. |

## Freshness Attributes

Sensors include source freshness attributes after a source has been fetched successfully:

| Attribute | Applies to | Meaning |
|-----------|------------|---------|
| `source_updated_noaa` | Solar Data | Last successful NOAA fetch. |
| `source_updated_hamqsl` | Solar Data | Last successful hamqsl fetch. |
| `source_updated_kc2g` | MUF Station | Last successful kc2g fetch. |
