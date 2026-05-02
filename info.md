# Amateur Radio Propagation

Surfaces real-time amateur radio propagation data as Home Assistant sensors.

## What you get

**Solar Data** (one instance)
- Solar Flux Index, Sunspot count, A/K indices, solar wind
- HF band conditions for 80m–10m (day & night)
- VHF aurora and E-skip conditions
- NOAA X-Ray class, flare data, G/S/R scales
- Real-time solar wind speed, Bz/Bt from NOAA
- Kp forecast, Dst index, predicted A-index and SFI, active region count

**MUF Station** (one per station)
- Maximum Usable Frequency (MUF) from the nearest ionosonde station
- foF2, foE, foEs, confidence score, layer heights
- Stale-data notification if the station goes offline

## Data sources

| Source | Data | Update |
|--------|------|--------|
| NOAA SWPC | X-Ray, solar wind, Kp, Dst, forecasts | 15 min |
| hamqsl.com | Solar indices, band conditions | 3 hr |
| kc2g.com | Ionosonde MUF/foF2 | 30 min |

## Requirements

- Home Assistant 2024.5.0 or later
- No additional packages required
