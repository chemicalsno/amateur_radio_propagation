"""Live connectivity smoke test for the Amateur Radio Propagation v2 integration.

Hits all three upstream endpoints and verifies the shape that the v2
coordinators expect to parse. Requires network access and aiohttp.

Run with:  python3 scripts/smoke_test.py
"""

from __future__ import annotations

import asyncio
import sys
from xml.etree import ElementTree as ET

import aiohttp

REQUEST_TIMEOUT = 30

URL_NOAA_XRAY = (
    "https://services.swpc.noaa.gov/json/goes/primary/xray-flares-latest.json"
)
URL_NOAA_SCALES = "https://services.swpc.noaa.gov/products/noaa-scales.json"
URL_NOAA_PROBABILITIES = "https://services.swpc.noaa.gov/json/solar_probabilities.json"
URL_NOAA_KP_1M = "https://services.swpc.noaa.gov/json/planetary_k_index_1m.json"
URL_NOAA_ALERTS = "https://services.swpc.noaa.gov/products/alerts.json"
URL_NOAA_PLASMA = (
    "https://services.swpc.noaa.gov/products/solar-wind/plasma-2-hour.json"
)
URL_NOAA_MAG = "https://services.swpc.noaa.gov/products/solar-wind/mag-2-hour.json"
URL_NOAA_KP_FORECAST = (
    "https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json"
)
URL_NOAA_DST = "https://services.swpc.noaa.gov/products/kyoto-dst.json"
URL_NOAA_PREDICTED_A = (
    "https://services.swpc.noaa.gov/json/predicted_fredericksburg_a_index.json"
)
URL_NOAA_PREDICTED_SFI = (
    "https://services.swpc.noaa.gov/json/predicted_f107cm_flux.json"
)
URL_NOAA_SOLAR_REGIONS = "https://services.swpc.noaa.gov/json/solar_regions.json"
URL_HAMQSL_XML = "https://www.hamqsl.com/solarxml.php"
URL_KC2G_STATIONS = "https://prop.kc2g.com/api/stations.json"

# Keys the SolarCoordinator reads from NOAA
# Note: API field is "max_class", which the coordinator maps to solar_xray_peak_class.
NOAA_KEYS = {"current_class", "begin_class", "end_class", "max_class", "current_ratio"}

# Keys the SolarCoordinator reads from hamqsl <solardata>
# Note: "electonflux" typo is canonical — it matches the upstream XML tag.
# Note: XML tag for Bz is "magneticfield", mapped to solar_bz in the coordinator.
HAMQSL_SCALAR_KEYS = {
    "solarflux",
    "sunspots",
    "aindex",
    "kindex",
    "magneticfield",
    "solarwind",
    "geomagfield",
    "signalnoise",
    "heliumline",
    "protonflux",
    "electonflux",
    "aurora",
    "latdegree",
    "fof2",
}
HAMQSL_BAND_KEYS = {
    ("80m-40m", "day"),
    ("80m-40m", "night"),
    ("30m-20m", "day"),
    ("30m-20m", "night"),
    ("17m-15m", "day"),
    ("17m-15m", "night"),
    ("12m-10m", "day"),
    ("12m-10m", "night"),
}
# VHF phenomena use (name, location) attributes — not (name, time)
HAMQSL_VHF_KEYS = {
    ("vhf-aurora", "northern_hemi"),
    ("E-Skip", "europe"),
    ("E-Skip", "north_america"),
    ("E-Skip", "europe_6m"),
    ("E-Skip", "europe_4m"),
}

# Keys the MufCoordinator reads per kc2g station record (top-level)
KC2G_RECORD_KEYS = {
    "mufd",
    "fof2",
    "foes",
    "foe",
    "cs",
    "time",
    "hme",
    "md",
    "hmf1",
    "hmf2",
    "scalef2",
    "yf2",
    "station",
}
KC2G_STATION_META = {"code", "name", "latitude", "longitude"}


def check(label: str, ok: bool, detail: str = "") -> bool:
    mark = "PASS" if ok else "FAIL"
    line = f"[{mark}] {label}"
    if detail:
        line += f"  ({detail})"
    print(line)
    return ok


async def main() -> int:
    failures = 0
    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        # ------------------------------------------------------------------
        # 1. NOAA X-Ray (JSON)
        # ------------------------------------------------------------------
        print("\n--- NOAA X-Ray ---")
        try:
            async with session.get(URL_NOAA_XRAY) as r:
                r.raise_for_status()
                entries = await r.json(content_type=None)

            failures += not check(
                "NOAA reachable", bool(entries), f"{len(entries)} entries"
            )
            if entries:
                entry = entries[0]
                missing = NOAA_KEYS - entry.keys()
                failures += not check(
                    "NOAA entry has all expected keys",
                    not missing,
                    f"missing={missing}"
                    if missing
                    else f"current_class={entry.get('current_class')!r}",
                )
        except Exception as err:
            failures += not check("NOAA reachable", False, str(err))

        # ------------------------------------------------------------------
        # 2. NOAA Solar Probabilities (JSON)
        # ------------------------------------------------------------------
        print("\n--- NOAA Solar Probabilities ---")
        try:
            async with session.get(URL_NOAA_PROBABILITIES) as r:
                r.raise_for_status()
                entries = await r.json(content_type=None)

            failures += not check(
                "NOAA probabilities reachable", bool(entries), f"{len(entries)} entries"
            )
            if entries:
                last = entries[-1]
                prob_keys = {
                    "m_class_1_day",
                    "x_class_1_day",
                    "m_class_3_day",
                    "x_class_3_day",
                    "polar_cap_absorption",
                }
                missing = prob_keys - last.keys()
                failures += not check(
                    "probabilities has expected keys",
                    not missing,
                    f"missing={missing}"
                    if missing
                    else f"m1={last.get('m_class_1_day')}% x1={last.get('x_class_1_day')}% pca={last.get('polar_cap_absorption')}",
                )
        except Exception as err:
            failures += not check("NOAA probabilities reachable", False, str(err))

        # ------------------------------------------------------------------
        # 3. NOAA Planetary K-Index 1-min (JSON)
        # ------------------------------------------------------------------
        print("\n--- NOAA Planetary K-Index (1m) ---")
        try:
            async with session.get(URL_NOAA_KP_1M) as r:
                r.raise_for_status()
                entries = await r.json(content_type=None)

            failures += not check(
                "NOAA kp_1m reachable", bool(entries), f"{len(entries)} entries"
            )
            if entries:
                last = entries[-1]
                if isinstance(last, list):
                    ok = len(last) >= 3 and isinstance(last[2], (int, float))
                    failures += not check(
                        "kp_1m array-of-arrays format, estimated_kp numeric",
                        ok,
                        f"estimated_kp={last[2]!r}" if ok else f"last={last!r}",
                    )
                elif isinstance(last, dict):
                    kp = last.get("estimated_kp")
                    failures += not check(
                        "kp_1m dict format, estimated_kp present",
                        kp is not None,
                        f"estimated_kp={kp!r}",
                    )
        except Exception as err:
            failures += not check("NOAA kp_1m reachable", False, str(err))

        # ------------------------------------------------------------------
        # 4. NOAA Space Weather Alerts (JSON)
        # ------------------------------------------------------------------
        print("\n--- NOAA Space Weather Alerts ---")
        try:
            async with session.get(URL_NOAA_ALERTS) as r:
                r.raise_for_status()
                entries = await r.json(content_type=None)

            failures += not check(
                "NOAA alerts reachable",
                isinstance(entries, list),
                f"{len(entries)} active alerts",
            )
            if entries:
                alert = entries[0]
                failures += not check(
                    "alert entry has message field",
                    "message" in alert,
                    f"product_id={alert.get('product_id')!r}",
                )
        except Exception as err:
            failures += not check("NOAA alerts reachable", False, str(err))

        # ------------------------------------------------------------------
        # 5. NOAA Solar Wind Plasma (JSON — array-of-arrays)
        # ------------------------------------------------------------------
        print("\n--- NOAA Solar Wind Plasma ---")
        try:
            async with session.get(URL_NOAA_PLASMA) as r:
                r.raise_for_status()
                entries = await r.json(content_type=None)

            failures += not check(
                "NOAA plasma reachable", len(entries) >= 2, f"{len(entries)} rows"
            )
            if len(entries) >= 2:
                last = entries[-1]
                ok = (
                    isinstance(last, list)
                    and len(last) >= 3
                    and (last[1] is None or isinstance(last[1], (int, float)))
                    and (last[2] is None or isinstance(last[2], (int, float)))
                )
                failures += not check(
                    "plasma last row has density[1] and speed[2]",
                    ok,
                    f"density={last[1]!r} speed={last[2]!r}" if ok else f"row={last!r}",
                )
        except Exception as err:
            failures += not check("NOAA plasma reachable", False, str(err))

        # ------------------------------------------------------------------
        # 6. NOAA Solar Wind Magnetometer (JSON — array-of-arrays)
        # ------------------------------------------------------------------
        print("\n--- NOAA Solar Wind Mag ---")
        try:
            async with session.get(URL_NOAA_MAG) as r:
                r.raise_for_status()
                entries = await r.json(content_type=None)

            failures += not check(
                "NOAA mag reachable", len(entries) >= 2, f"{len(entries)} rows"
            )
            if len(entries) >= 2:
                last = entries[-1]
                ok = (
                    isinstance(last, list)
                    and len(last) >= 7
                    and (last[3] is None or isinstance(last[3], (int, float)))
                    and (last[6] is None or isinstance(last[6], (int, float)))
                )
                failures += not check(
                    "mag last row has bz_gsm[3] and bt[6]",
                    ok,
                    f"bz={last[3]!r} bt={last[6]!r}" if ok else f"row={last!r}",
                )
        except Exception as err:
            failures += not check("NOAA mag reachable", False, str(err))

        # ------------------------------------------------------------------
        # 7. NOAA Kp Forecast (JSON — array-of-dicts)
        # ------------------------------------------------------------------
        print("\n--- NOAA Kp Forecast ---")
        try:
            async with session.get(URL_NOAA_KP_FORECAST) as r:
                r.raise_for_status()
                entries = await r.json(content_type=None)

            failures += not check(
                "NOAA kp_forecast reachable", bool(entries), f"{len(entries)} entries"
            )
            if entries:
                predicted = next(
                    (
                        e
                        for e in entries
                        if isinstance(e, dict) and e.get("observed") == "predicted"
                    ),
                    None,
                )
                failures += not check(
                    "kp_forecast has a 'predicted' entry",
                    predicted is not None,
                    f"kp={predicted.get('kp')!r}" if predicted else "not found",
                )
        except Exception as err:
            failures += not check("NOAA kp_forecast reachable", False, str(err))

        # ------------------------------------------------------------------
        # 8. NOAA Kyoto Dst (JSON — array-of-dicts)
        # ------------------------------------------------------------------
        print("\n--- NOAA Dst ---")
        try:
            async with session.get(URL_NOAA_DST) as r:
                r.raise_for_status()
                entries = await r.json(content_type=None)

            failures += not check(
                "NOAA dst reachable", bool(entries), f"{len(entries)} entries"
            )
            if entries:
                last = entries[-1]
                ok = isinstance(last, dict) and "dst" in last
                failures += not check(
                    "dst last entry has 'dst' key",
                    ok,
                    f"dst={last.get('dst')!r}" if ok else f"keys={list(last.keys())!r}",
                )
        except Exception as err:
            failures += not check("NOAA dst reachable", False, str(err))

        # ------------------------------------------------------------------
        # 9. NOAA Predicted A-Index (JSON — array-of-dicts)
        # ------------------------------------------------------------------
        print("\n--- NOAA Predicted A-Index ---")
        try:
            async with session.get(URL_NOAA_PREDICTED_A) as r:
                r.raise_for_status()
                entries = await r.json(content_type=None)

            failures += not check(
                "NOAA predicted_a reachable", bool(entries), f"{len(entries)} entries"
            )
            if entries:
                first = entries[0]
                a_keys = {"afred_1_day", "afred_2_day", "afred_3_day"}
                missing = a_keys - first.keys()
                failures += not check(
                    "predicted_a has 1/2/3-day keys",
                    not missing,
                    f"missing={missing}"
                    if missing
                    else f"1d={first.get('afred_1_day')} 2d={first.get('afred_2_day')} 3d={first.get('afred_3_day')}",
                )
        except Exception as err:
            failures += not check("NOAA predicted_a reachable", False, str(err))

        # ------------------------------------------------------------------
        # 10. NOAA Predicted SFI (JSON — array-of-dicts)
        # ------------------------------------------------------------------
        print("\n--- NOAA Predicted SFI ---")
        try:
            async with session.get(URL_NOAA_PREDICTED_SFI) as r:
                r.raise_for_status()
                entries = await r.json(content_type=None)

            failures += not check(
                "NOAA predicted_sfi reachable", bool(entries), f"{len(entries)} entries"
            )
            if entries:
                first = entries[0]
                ok = "tencmfcst_1_day" in first
                failures += not check(
                    "predicted_sfi has tencmfcst_1_day",
                    ok,
                    f"value={first.get('tencmfcst_1_day')!r}"
                    if ok
                    else f"keys={list(first.keys())!r}",
                )
        except Exception as err:
            failures += not check("NOAA predicted_sfi reachable", False, str(err))

        # ------------------------------------------------------------------
        # 11. NOAA Solar Regions (JSON — array-of-dicts)
        # ------------------------------------------------------------------
        print("\n--- NOAA Solar Regions ---")
        try:
            async with session.get(URL_NOAA_SOLAR_REGIONS) as r:
                r.raise_for_status()
                entries = await r.json(content_type=None)

            failures += not check(
                "NOAA solar_regions reachable",
                isinstance(entries, list),
                f"{len(entries)} entries",
            )
            if entries:
                first = entries[0]
                ok = "observed_date" in first
                failures += not check(
                    "solar_regions entry has observed_date",
                    ok,
                    f"observed_date={first.get('observed_date')!r}"
                    if ok
                    else f"keys={list(first.keys())!r}",
                )
        except Exception as err:
            failures += not check("NOAA solar_regions reachable", False, str(err))

        # ------------------------------------------------------------------
        # 12. hamqsl.com XML
        # ------------------------------------------------------------------
        print("\n--- hamqsl.com ---")
        try:
            async with session.get(URL_HAMQSL_XML) as r:
                r.raise_for_status()
                body = await r.text()

            root = ET.fromstring(body)
            sd = root.find("solardata")
            failures += not check(
                "hamqsl reachable + solardata element present", sd is not None
            )

            if sd is not None:
                missing_scalars = {k for k in HAMQSL_SCALAR_KEYS if sd.find(k) is None}
                failures += not check(
                    "hamqsl scalar fields",
                    not missing_scalars,
                    f"missing={missing_scalars}"
                    if missing_scalars
                    else f"solarflux={(sd.findtext('solarflux') or '').strip()}",
                )

                bands_el = sd.find("calculatedconditions")
                found_bands: set[tuple[str, str]] = set()
                if bands_el is not None:
                    for b in bands_el.findall("band"):
                        found_bands.add((b.get("name", ""), b.get("time", "")))
                missing_bands = HAMQSL_BAND_KEYS - found_bands
                failures += not check(
                    "hamqsl HF band entries",
                    not missing_bands,
                    f"missing={missing_bands}" if missing_bands else "all 8 HF bands",
                )

                vhf_el = sd.find("calculatedvhfconditions")
                found_vhf: set[tuple[str, str]] = set()
                if vhf_el is not None:
                    for b in vhf_el.findall("phenomenon"):
                        found_vhf.add((b.get("name", ""), b.get("location", "")))
                missing_vhf = HAMQSL_VHF_KEYS - found_vhf
                failures += not check(
                    "hamqsl VHF phenomenon entries",
                    not missing_vhf,
                    f"missing={missing_vhf}" if missing_vhf else "all 5 VHF phenomena",
                )

        except Exception as err:
            failures += not check("hamqsl reachable", False, str(err))

        # ------------------------------------------------------------------
        # 13. kc2g ionosonde stations (JSON)
        # ------------------------------------------------------------------
        print("\n--- kc2g stations ---")
        try:
            async with session.get(URL_KC2G_STATIONS) as r:
                r.raise_for_status()
                stations = await r.json(content_type=None)

            failures += not check(
                "kc2g reachable", bool(stations), f"{len(stations)} stations"
            )

            if stations:
                sample = stations[0]
                missing_record = KC2G_RECORD_KEYS - sample.keys()
                failures += not check(
                    "kc2g station record keys",
                    not missing_record,
                    f"missing={missing_record}"
                    if missing_record
                    else "all record keys",
                )

                meta = sample.get("station") or {}
                missing_meta = KC2G_STATION_META - meta.keys()
                failures += not check(
                    "kc2g station.station meta keys",
                    not missing_meta,
                    f"missing={missing_meta}"
                    if missing_meta
                    else f"code={meta.get('code')!r}",
                )

                failures += not check(
                    "kc2g mufd is numeric",
                    isinstance(sample.get("mufd"), (int, float)),
                    f"mufd={sample.get('mufd')!r}",
                )
                failures += not check(
                    "kc2g cs is numeric",
                    isinstance(sample.get("cs"), (int, float)),
                    f"cs={sample.get('cs')!r}",
                )
        except Exception as err:
            failures += not check("kc2g reachable", False, str(err))

    print()
    if failures == 0:
        print("ALL GOOD")
    else:
        print(f"{failures} FAILURE(S)")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
