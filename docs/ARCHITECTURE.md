# Architecture

This integration is a Home Assistant custom integration under `custom_components/amateur_radio_propagation/`.

## Core Modules

| File | Responsibility |
|------|----------------|
| `manifest.json` | Integration metadata, Home Assistant version floor, issue tracker, and integration type. |
| `__init__.py` | Config entry setup/unload, coordinator creation, platform forwarding, runtime data storage. |
| `config_flow.py` | Setup, reconfigure, options flow, station list lookup, duplicate entry checks. |
| `const.py` | Domain constants, URLs, update intervals, sensor descriptions, config keys. |
| `coordinator_solar.py` | NOAA and hamqsl fetch, parse, merge, freshness tracking, repair issues. |
| `coordinator_muf.py` | kc2g station fetch, parse, staleness checks, repair issues. |
| `sensor.py` | Sensor entity creation, device info, unique IDs, availability, freshness attributes. |
| `diagnostics.py` | Redacted diagnostics export. |
| `dashboard_notify.py` | Optional local notification that points users to bundled dashboard examples. |
| `repairs.py` | Repair flow behavior. |

## Config Entry Types

The setup flow asks the user to choose one of two modes:

| Choice | Purpose | Multiplicity |
|--------|---------|--------------|
| `solar` | Global solar, HF/VHF, aurora, and NOAA space-weather data. | One entry. |
| `muf` | One kc2g ionosonde station. | One entry per station. |

MUF entries store the selected `station_code` and `station_name`. Reconfigure can be used to switch stations.

## Coordinators

The integration uses Home Assistant `DataUpdateCoordinator` objects.

### Solar Coordinator

`SolarCoordinator` combines NOAA and hamqsl data into one coordinator payload.

| Source | Interval | Data |
|--------|----------|------|
| NOAA SWPC fast endpoints | 15 min | X-ray, solar wind, Kp, Dst, forecasts, alerts. |
| NOAA SWPC solar regions | 3 hr | Active solar region count. |
| hamqsl.com | 3 hr | Solar indices, HF band conditions, VHF, aurora. |

The coordinator keeps previous values when an upstream source has a temporary failure after a successful fetch. It records source freshness timestamps for successful NOAA and hamqsl fetches.

### MUF Coordinator

`MufCoordinator` polls kc2g station data every 30 minutes for one station. It maps fields from the kc2g station record into station-specific keys such as `solar_hf_muf_<station>`.

If a station record is older than the configured stale threshold, the coordinator creates a Home Assistant repair issue. The default stale threshold is 3 hours and can be adjusted in entry options.

## Parsing And Error Handling

Upstream parsing is isolated in coordinator helper functions. Malformed payloads, HTTP errors, JSON/XML parsing failures, and timeouts are converted to `UpdateFailed` where appropriate.

When there is no previous data, update failures make entities unavailable. When previous data exists, transient failures keep the last known values and log the source failure.

## Sensors

`sensor.py` builds entities from `SensorEntityDescription` definitions.

Entity behavior:

- `unique_id` is based on config entry ID and sensor key.
- `entity_id` is based on the integration domain and slugified sensor key.
- Availability follows whether the coordinator has a non-`None` value for that sensor key.
- Device info uses a service device entry for the config entry.
- Freshness attributes are exposed when successful source timestamps are available.

## Diagnostics

Diagnostics are exported through `diagnostics.py` and redact sensitive or user-specific station fields. The integration does not require credentials.

## Repairs

Repair issues are used for stale station data and source freshness problems that require user awareness. MUF station repair messages include station name, station code, and last reported station time so the user can decide whether to reconfigure.

## Tests

Tests live in `tests/` and cover:

- Config flow and reconfigure behavior.
- Solar and MUF coordinator parsing.
- Sensor entity metadata and availability.
- Diagnostics redaction.
- Dashboard YAML validity and entity references.
- Packaging and metadata expectations.
- Home Assistant quality scale checks.

Run the suite with:

```bash
pytest --asyncio-mode=auto tests/
```
