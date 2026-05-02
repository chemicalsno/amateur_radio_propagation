# Changelog

## [Unreleased]

No unreleased changes.

## [2.1.0] - 2026-05-02

### Highlights

- State-based icons and state translations for HF band conditions and NOAA G/S/R storm scales.
- Semantic pull request title validation.
- Updated default HF condition icons from generic wave icons to signal-bar icons.
- Kept explicit default icons for ionosonde and foF2 sensors while adding dynamic state icon mappings.
- Bumped integration version to 2.1.0.

## [2.0.0] - 2026-05-02

Initial public release.

### Highlights

- Adds Home Assistant UI setup for global solar data and per-station MUF data.
- Provides sensors for solar indices, HF band conditions, VHF/aurora indicators, NOAA space-weather scales, flare probabilities, solar wind, Kp/Dst forecasts, active solar regions, and kc2g ionosonde readings.
- Uses NOAA SWPC, hamqsl.com, and kc2g.com as data sources with source freshness attributes.
- Includes repair issues for stale NOAA or ionosonde station data.
- Bundles dashboard examples for standard Lovelace and popular HACS frontend cards.
- Includes translations, icons, diagnostics redaction, HACS metadata, Hassfest validation, and automated tests.

### Requirements

- Home Assistant 2024.5.0 or later.
- No additional runtime Python packages.
