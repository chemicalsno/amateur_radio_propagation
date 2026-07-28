#!/usr/bin/env python3
"""Sync the curated dashboards bundled in the integration with the root examples.

The integration bundles a curated subset of the ``dashboards/`` examples inside
``custom_components/amateur_radio_propagation/dashboards/`` because HACS only
ships the component directory, and ``dashboard_notify`` reads those files at
runtime to build the MUF setup notification. The bundled copies must stay
byte-identical to the root examples (enforced by
``tests/test_metadata.py::test_installed_curated_dashboards_match_root_examples``).

The bundled directory listing *is* the curated set — every ``*.yaml`` in it must
have a matching root example.

Usage:
    python scripts/sync_dashboards.py            # copy root -> bundled
    python scripts/sync_dashboards.py --check     # exit 1 if any copy is stale
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_ROOT_DASHBOARDS = _REPO_ROOT / "dashboards"
_BUNDLED_DASHBOARDS = (
    _REPO_ROOT / "custom_components" / "amateur_radio_propagation" / "dashboards"
)


def _curated_files() -> list[Path]:
    """Return the bundled dashboard files; the bundled dir defines the set."""
    return sorted(_BUNDLED_DASHBOARDS.glob("*.yaml"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify bundled copies match root examples; exit 1 if any differ.",
    )
    args = parser.parse_args()

    stale: list[str] = []
    missing_root: list[str] = []

    for bundled in _curated_files():
        root = _ROOT_DASHBOARDS / bundled.name
        if not root.is_file():
            missing_root.append(bundled.name)
            continue
        root_text = root.read_text(encoding="utf-8")
        if bundled.read_text(encoding="utf-8") == root_text:
            continue
        stale.append(bundled.name)
        if not args.check:
            bundled.write_text(root_text, encoding="utf-8")

    for name in missing_root:
        print(f"WARNING: bundled '{name}' has no root example in dashboards/")

    if args.check:
        if stale:
            print("Bundled dashboards are out of sync with root examples:")
            for name in stale:
                print(f"  - {name}")
            print("Run: python scripts/sync_dashboards.py")
            return 1
        print("Bundled dashboards are in sync.")
        return 1 if missing_root else 0

    if stale:
        print("Synced bundled dashboards from root examples:")
        for name in stale:
            print(f"  - {name}")
    else:
        print("Bundled dashboards already in sync; nothing to do.")
    return 1 if missing_root else 0


if __name__ == "__main__":
    sys.exit(main())
