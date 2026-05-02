# Troubleshooting

## Sensors Show `unavailable`

The coordinator did not produce a value for that entity.

Check:

- **Settings -> System -> Logs** for errors from `amateur_radio_propagation`.
- Whether the upstream source is temporarily unavailable.
- Whether the sensor is a diagnostic entity that has been enabled but the upstream feed does not currently publish that field.

The integration retries automatically on the next polling cycle.

## MUF Station Data Is Stale

A repair issue appears when station data is older than the configured stale threshold.

Common causes:

- The ionosonde station is offline.
- The kc2g feed has not received a fresh station report.
- The selected station is no longer present in the feed.

Actions:

- Open **Settings -> Repairs** and review the station name, station code, and last reported time.
- Use **Reconfigure** on the MUF entry to choose a different station.
- Adjust the stale threshold in the entry options if your station commonly reports less frequently.

## Solar Data Stopped Updating

Solar Data combines NOAA and hamqsl feeds. One source can fail while the other continues updating.

Check:

- `source_updated_noaa` and `source_updated_hamqsl` attributes.
- Home Assistant logs for HTTP errors or timeouts.
- Whether hamqsl.com or NOAA SWPC endpoints are temporarily unavailable.

When previous data exists, the coordinator keeps last known values during transient failures.

## Missing Solar Sensors

Some sensors are disabled by default because they are diagnostic or low-level fields.

To enable them:

1. Go to **Settings -> Devices & Services**.
2. Open **Amateur Radio Propagation**.
3. Open the entity list.
4. Enable the specific diagnostic entity.

## Config Flow Cannot Connect To Station List

The setup flow fetches the kc2g station list when configuring a MUF entry.

Check:

- Home Assistant has internet access.
- The kc2g endpoint is reachable.
- The error is not a temporary upstream outage.

Retry setup after the upstream endpoint recovers.

## Duplicate Entry Errors

Solar Data can only be configured once. Each MUF station can only be configured once.

Use **Reconfigure** if you want to change an existing MUF station. Delete the old entry first if you want to recreate it from scratch.

## Dashboard Shows Missing Entities

Dashboard examples use expected entity IDs. Your entity IDs may differ if Home Assistant added a suffix or if your MUF station code is different.

Check:

- Replace sample station codes such as `IF843` or `if843` with your configured station code.
- Confirm entity IDs under **Settings -> Devices & Services -> Entities**.
- Plugin dashboards require their matching custom frontend cards to be installed.

## Graph Cards Stay Loading

Some custom graph cards can hang when an entity has no history at all.

Options:

- Remove entities that have never produced data from that graph card.
- Use separate cards so one missing history series does not block a larger graph.
- Prefer entities with stable history for multi-series graph cards.

## Live Smoke Test

The optional smoke test calls live NOAA, hamqsl, and kc2g endpoints:

```bash
python scripts/smoke_test.py
```

Use it only when you want to verify current upstream reachability. It is not part of the isolated test suite.
