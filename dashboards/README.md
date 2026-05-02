# Example Dashboards

Example dashboards covering different use cases and dependency levels.

| File | Dependencies | Best for |
|------|-------------|----------|
| `vanilla-dashboard.yaml` | None | Quickest start, works with any HA install |
| `embedded-descriptions-dashboard.yaml` | None | Descriptions always visible as inline markdown |
| `operator-go-no-go-dashboard.yaml` | None | Fast operating decision dashboard |
| `contest-field-day-dashboard.yaml` | None | Dense contest or Field Day operating desk |
| `muf-station-dashboard.yaml` | None | Dedicated ionosonde station monitoring |
| `space-weather-alert-center.yaml` | None | NOAA alerts, G/S/R scales, flare risk |
| `vhf-6m-opening-dashboard.yaml` | None | VHF, 6m, E-skip, and aurora watch |
| `diagnostics-freshness-dashboard.yaml` | None | Source freshness and support diagnostics |
| `mobile-minimal-dashboard.yaml` | None | Compact phone-first operating view |
| `bubble-card-dashboard.yaml` | `custom:bubble-card` | Mobile and desktop — tap ⓘ to open section descriptions |
| `mushroom-operator-dashboard.yaml` | Mushroom cards | Clean mobile/desktop operator console |
| `mini-graph-trends-dashboard.yaml` | `custom:mini-graph-card` | Trend-focused solar and MUF history |
| `apexcharts-correlation-dashboard.yaml` | `custom:apexcharts-card` | Correlation charts for SFI, MUF, Kp, Bz, TEC |
| `auto-entities-maintenance-dashboard.yaml` | `custom:auto-entities` | Automatically grouped maintenance lists |
| `layout-card-desktop-dashboard.yaml` | `custom:layout-card` | Responsive desktop operating console |
| `state-switch-browser-mod-dashboard.yaml` | `custom:state-switch` + `browser_mod` | Different mobile/desktop layouts with popups |
| `button-card-status-matrix-dashboard.yaml` | `custom:button-card` | Compact color-coded band status matrix |
| `amateur-radio-propagation.yaml` | `custom:button-card` | Desktop — hover tooltips on each tile |
| `browser-mod-dashboard.yaml` | `custom:button-card` + `browser_mod` | Desktop — tap opens a popup (requires per-browser setup) |

## Installation

Home Assistant does not support dashboard blueprints. Use one of the supported dashboard workflows:

1. Copy the dashboard YAML files you want into `/config/dashboards/`.
2. Add them under `lovelace.dashboards` in `configuration.yaml`.
3. Restart Home Assistant or reload Lovelace resources where applicable.

Example:

```yaml
lovelace:
  mode: storage
  dashboards:
    arp-operator:
      mode: yaml
      title: Propagation Go/No-Go
      icon: mdi:radio-tower
      show_in_sidebar: true
      filename: dashboards/operator-go-no-go-dashboard.yaml
    arp-space-weather:
      mode: yaml
      title: Space Weather
      icon: mdi:weather-lightning
      show_in_sidebar: true
      filename: dashboards/space-weather-alert-center.yaml
```

The file `lovelace-dashboards.example.yaml` contains a larger ready-to-use `dashboards:` map. You can include it from `configuration.yaml`:

```yaml
lovelace:
  mode: storage
  dashboards: !include dashboards/lovelace-dashboards.example.yaml
```

For a single dashboard, you can also paste the YAML contents into a Lovelace dashboard via **Edit → Raw configuration editor**.

## Station code

Dashboards with ionosonde sections use `IF843` as a placeholder station code. Find and replace `IF843` / `if843` with your own station code throughout before pasting.

Your station code is shown in **Settings → Devices & Services → Amateur Radio Propagation** (MUF entry).

## Custom card dependencies

- **`custom:bubble-card`** — install via HACS → Frontend; no per-device setup required
- **`custom:button-card`** — install via HACS → Frontend
- **Mushroom cards** — install via HACS → Frontend
- **`custom:mini-graph-card`** — install via HACS → Frontend
- **`custom:apexcharts-card`** — install via HACS → Frontend
- **`custom:auto-entities`** — install via HACS → Frontend
- **`custom:layout-card`** — install via HACS → Frontend
- **`custom:state-switch`** — install via HACS → Frontend
- **`browser_mod`** — install via HACS → Integrations; requires browser_mod v2+ and per-browser registration
