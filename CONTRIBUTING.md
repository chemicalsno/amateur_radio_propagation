# Contributing

## Development Setup

Requires Python 3.12+ and [`uv`](https://github.com/astral-sh/uv).

```bash
uv sync --frozen
```

## Running Tests

```bash
# All tests
uv run pytest --asyncio-mode=auto tests/

# Single test file
uv run pytest --asyncio-mode=auto tests/test_solar_coordinator.py

# Single test
uv run pytest --asyncio-mode=auto tests/test_init.py::test_solar_setup_and_unload

# Type checks
uv run pyright

# Formatting and lint
uv run ruff format --check custom_components tests scripts
uv run ruff check custom_components tests scripts

# Smoke test against real APIs (no HA needed)
uv run python scripts/smoke_test.py
```

## Project Structure

```
custom_components/amateur_radio_propagation/
  __init__.py          # Entry setup/unload
  const.py             # URLs, poll intervals, sensor descriptions, Choice enum
  coordinator_solar.py # NOAA + hamqsl + kc2g foEs polling
  coordinator_muf.py   # kc2g ionosonde polling
  config_flow.py       # UI config flow (solar vs MUF, station selection)
  sensor.py            # HamRadioSensor entity
  diagnostics.py       # Redacted diagnostics export
  dashboard_notify.py  # One-time dashboard notification for MUF entries
  types.py             # Typed config entry alias
  strings.json         # Config flow strings (source of truth)
  translations/en.json # English translations
  manifest.json
tests/
  conftest.py
  test_init.py
  test_solar_coordinator.py
  test_muf_coordinator.py
  test_config_flow.py
  test_dashboard_notify.py
  test_diagnostics.py
  test_metadata.py
  test_sensor.py
```

## Code Conventions

**Coordinators:** Each coordinator owns its own data fetching and parsing. Parse helpers raise `UpdateFailed` on malformed payloads. `SolarCoordinator._async_update_data` logs per-source failures and keeps the last known values for that source, and raises `UpdateFailed` only when no source produced data. HTTP requests use `asyncio.timeout(REQUEST_TIMEOUT)` with `await req.text()` inside the context manager.

**Datetime:** Always use `dt_util.utcnow()` and `dt_util.parse_datetime()` from `homeassistant.util.dt`. Never `datetime.now()`.

**Sensors:** `HamRadioSensor.available` returns `False` when `native_value is None`. `_handle_coordinator_update` delegates to `super()._handle_coordinator_update()`.

**Sensor keys:**
- Solar: plain strings — `solar_flux_index`, `solar_xray`
- MUF: `solar_hf_{field}_{station_code}` — e.g. `solar_hf_muf_BC840`
- The `mufd → muf` rename in `_KC2G_STATION_FIELDS` is intentional (legacy entity ID)
- The `electonflux` typo in `_HAMQSL_SCALAR_KEYS` is canonical (matches upstream XML)

**Sensor buckets:**
- Core / A / B: `entity_registry_enabled_default=True`
- C: `entity_registry_enabled_default=False`, `EntityCategory.DIAGNOSTIC`

## Testing Approach

Tests mock `_async_update_data` at the coordinator level. Never hit real APIs in tests. The `auto_enable_custom_integrations` fixture in `conftest.py` is required for HA to load the custom component in tests.

When adding a new sensor, add it to both `const.py` (or `_muf_descriptions`) and the corresponding coordinator test's return value.

## Pull Requests

- Keep PRs focused — one logical change per PR
- Tests must pass: `uv run pytest --asyncio-mode=auto tests/`
- Type and style checks must pass: `pyright`, `ruff format --check`, and `ruff check`
- Match existing code style — no new dependencies without discussion
- Update `CHANGELOG.md` under an `[Unreleased]` section

## Reporting Issues

Open an issue at `https://github.com/chemicalsno/amateur_radio_propagation/issues` with:
- Home Assistant version
- Integration version
- Relevant log lines from **Settings → System → Logs** (filter for `amateur_radio_propagation`)
