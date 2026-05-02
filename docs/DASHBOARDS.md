# Dashboard Reference

Example Lovelace dashboards live in `dashboards/`. They are optional starting points and can be copied, renamed, and edited for your station code and installed frontend cards.

## Dashboard Catalog

| File | Dependencies | Best for |
|------|--------------|----------|
| `vanilla-dashboard.yaml` | None | Quickest start, works with any Home Assistant install. |
| `embedded-descriptions-dashboard.yaml` | None | Inline markdown explanations for each group. |
| `operator-go-no-go-dashboard.yaml` | None | Fast operating decision dashboard. |
| `contest-field-day-dashboard.yaml` | None | Dense contest or Field Day operating desk. |
| `muf-station-dashboard.yaml` | None | Dedicated ionosonde station monitoring. |
| `space-weather-alert-center.yaml` | None | NOAA alerts, G/S/R scales, and flare risk. |
| `vhf-6m-opening-dashboard.yaml` | None | VHF, 6m, E-skip, and aurora watch. |
| `diagnostics-freshness-dashboard.yaml` | None | Source freshness and support diagnostics. |
| `mobile-minimal-dashboard.yaml` | None | Compact phone-first operating view. |
| `bubble-card-dashboard.yaml` | `custom:bubble-card` | Mobile and desktop sections with tap-to-open descriptions. |
| `mushroom-operator-dashboard.yaml` | Mushroom cards | Clean mobile/desktop operator console. |
| `mini-graph-trends-dashboard.yaml` | `custom:mini-graph-card` | Trend-focused solar and MUF history. |
| `apexcharts-correlation-dashboard.yaml` | `custom:apexcharts-card` | Correlation charts for SFI, MUF, Kp, Bz, and related indices. |
| `auto-entities-maintenance-dashboard.yaml` | `custom:auto-entities` | Automatically grouped maintenance and entity lists. |
| `layout-card-desktop-dashboard.yaml` | `custom:layout-card` | Responsive desktop operating console. |
| `state-switch-browser-mod-dashboard.yaml` | `custom:state-switch`, `browser_mod` | Different mobile and desktop layouts with popups. |
| `button-card-status-matrix-dashboard.yaml` | `custom:button-card` | Compact color-coded band status matrix. |
| `amateur-radio-propagation.yaml` | `custom:button-card` | Desktop dashboard with hover tooltips. |
| `browser-mod-dashboard.yaml` | `custom:button-card`, `browser_mod` | Desktop dashboard with tap-to-open popups. |

## Manual Import

1. In Home Assistant, go to **Settings -> Dashboards -> Add Dashboard**.
2. Give it a name, choose an icon, and select **YAML mode**.
3. Open the new dashboard.
4. Select the three-dot menu, then **Raw configuration editor**.
5. Paste the contents of the dashboard YAML file.
6. Save.

If the dashboard references a sample MUF station, replace `IF843` and `if843` with your configured station code.

## YAML Dashboard Registration

You can copy dashboard YAML files into `/config/dashboards/` and register them in `configuration.yaml`:

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
```

For a larger ready-to-use map, copy `dashboards/lovelace-dashboards.example.yaml` into `/config/dashboards/` and include it:

```yaml
lovelace:
  mode: storage
  dashboards: !include dashboards/lovelace-dashboards.example.yaml
```

Restart Home Assistant after changing `configuration.yaml`.

## Plugin Notes

Plugin dashboards require their matching frontend cards to be installed before the dashboard can render correctly.

| Plugin | Common install path | Notes |
|--------|---------------------|-------|
| Bubble Card | HACS frontend | Good for collapsible mobile sections. |
| Mushroom | HACS frontend | Good for clean entity-heavy dashboards. |
| mini-graph-card | HACS frontend | Useful for history trends. Avoid entities that have never produced history, because some graph cards may stay in a loading state. |
| ApexCharts Card | HACS frontend | Useful for multi-series comparisons and correlation views. |
| auto-entities | HACS frontend | Useful when you want dashboards to adapt as entities are enabled. |
| layout-card | HACS frontend | Useful for desktop grid layouts. |
| state-switch | HACS frontend | Useful for separate mobile and desktop views. |
| browser_mod | HACS frontend plus browser registration | Useful for popups, but requires per-browser setup. |
| button-card | HACS frontend | Useful for compact status matrices and heavily styled tiles. |

## Entity Replacement

Dashboard examples use the integration's generated entity IDs. For MUF station dashboards, replace the sample station code with your configured station code.

Example:

```text
sensor.amateur_radio_propagation_solar_hf_muf_if843
```

If your station code is `BC840`, use:

```text
sensor.amateur_radio_propagation_solar_hf_muf_bc840
```

Home Assistant entity IDs are lowercase even when the station code is displayed in uppercase elsewhere.
