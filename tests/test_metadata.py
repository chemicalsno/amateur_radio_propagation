"""Tests for integration metadata files."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
import yaml  # type: ignore[import-untyped]

from custom_components.amateur_radio_propagation.const import SENSOR_TYPES, VERSION
from custom_components.amateur_radio_propagation.sensor import _muf_descriptions

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "amateur_radio_propagation"
TRANSLATIONS = INTEGRATION / "translations"
DASHBOARDS = ROOT / "dashboards"
INSTALLED_DASHBOARDS = INTEGRATION / "dashboards"
PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")
DASHBOARD_ENTITY_RE = re.compile(r"sensor\.amateur_radio_propagation_[a-zA-Z0-9_]+")
CURATED_DASHBOARDS = (
    "bubble-card-dashboard.yaml",
    "embedded-descriptions-dashboard.yaml",
    "mini-graph-trends-dashboard.yaml",
    "muf-station-dashboard.yaml",
    "mushroom-operator-dashboard.yaml",
    "vanilla-dashboard.yaml",
)


class UniqueKeyLoader(yaml.SafeLoader):  # type: ignore[misc]
    """YAML loader that rejects duplicate mapping keys."""


def _construct_mapping_unique_keys(
    loader: UniqueKeyLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        value = loader.construct_object(value_node, deep=deep)
        mapping[key] = value
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping_unique_keys,
)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def _string_leaves(
    data: Any, prefix: tuple[str, ...] = ()
) -> dict[tuple[str, ...], str]:
    if isinstance(data, str):
        return {prefix: data}
    if isinstance(data, dict):
        leaves: dict[tuple[str, ...], str] = {}
        for key, value in data.items():
            leaves.update(_string_leaves(value, (*prefix, str(key))))
        return leaves
    return {}


def _placeholders(value: str) -> set[str]:
    return set(PLACEHOLDER_RE.findall(value))


def _root_relative_id(path: Path) -> str:
    return str(path.relative_to(ROOT))


def _path_name_id(path: Path) -> str:
    return path.name


def _dashboard_files() -> list[Path]:
    return sorted(DASHBOARDS.glob("*.yaml")) + sorted(
        INSTALLED_DASHBOARDS.glob("*.yaml")
    )


def _known_dashboard_entities() -> set[str]:
    known = {f"sensor.amateur_radio_propagation_{desc.key}" for desc in SENSOR_TYPES}
    known.update(
        f"sensor.amateur_radio_propagation_{desc.key.lower()}"
        for desc in _muf_descriptions("IF843")
    )
    return known


def _disabled_default_dashboard_entities() -> set[str]:
    disabled = {
        f"sensor.amateur_radio_propagation_{desc.key}"
        for desc in SENSOR_TYPES
        if desc.entity_registry_enabled_default is False
    }
    disabled.update(
        f"sensor.amateur_radio_propagation_{desc.key.lower()}"
        for desc in _muf_descriptions("IF843")
        if desc.entity_registry_enabled_default is False
    )
    return disabled


@pytest.mark.parametrize(
    "path",
    [
        ROOT / "hacs.json",
        INTEGRATION / "icons.json",
        INTEGRATION / "manifest.json",
        INTEGRATION / "strings.json",
        *sorted(TRANSLATIONS.glob("*.json")),
    ],
    ids=_root_relative_id,
)
def test_json_metadata_is_valid(path: Path) -> None:
    """JSON metadata files parse successfully."""
    _load_json(path)


def test_quality_scale_yaml_is_valid_without_duplicate_keys() -> None:
    """Quality scale metadata parses as YAML and has no duplicate keys."""
    data = yaml.load(
        (INTEGRATION / "quality_scale.yaml").read_text(),
        Loader=UniqueKeyLoader,
    )

    assert isinstance(data, dict)
    assert isinstance(data.get("rules"), dict)


def test_hacs_and_manifest_versions_are_consistent() -> None:
    """HACS and manifest metadata expose release and compatibility versions."""
    hacs = _load_json(ROOT / "hacs.json")
    manifest = _load_json(INTEGRATION / "manifest.json")

    assert hacs["homeassistant"] == "2024.5.0"
    assert manifest["version"] == VERSION


def test_manifest_contains_hacs_required_urls() -> None:
    """Manifest includes public documentation and issue tracker URLs."""
    manifest = _load_json(INTEGRATION / "manifest.json")

    assert manifest["documentation"].startswith("https://github.com/")
    assert manifest["issue_tracker"].startswith("https://github.com/")


def test_local_brand_assets_use_supported_filenames() -> None:
    """Local brand images use Home Assistant's supported custom integration names."""
    brand = INTEGRATION / "brand"

    assert (brand / "icon.png").is_file()
    assert (brand / "dark_icon.png").is_file()
    assert (brand / "logo.png").is_file()
    assert (brand / "dark_logo.png").is_file()
    assert not list(ROOT.glob("icon-*.PNG"))


def test_root_hacs_brand_icon_matches_integration_icon() -> None:
    """Root brand icon is present for HACS validation and matches local brand."""
    root_icon = ROOT / "brand" / "icon.png"
    integration_icon = INTEGRATION / "brand" / "icon.png"

    assert root_icon.is_file()
    assert root_icon.read_bytes() == integration_icon.read_bytes()


def test_icons_cover_all_sensor_translation_keys() -> None:
    """Every sensor translation key has an integration icon definition."""
    icons = _load_json(INTEGRATION / "icons.json")["entity"]["sensor"]
    sensor_keys = {desc.translation_key or desc.key for desc in SENSOR_TYPES}
    sensor_keys.update(
        desc.translation_key or desc.key for desc in _muf_descriptions("IF843")
    )

    assert sensor_keys <= set(icons)


@pytest.mark.parametrize("path", _dashboard_files(), ids=_root_relative_id)
def test_dashboard_yaml_is_valid(path: Path) -> None:
    """Dashboard example YAML files parse successfully."""
    data = yaml.load(path.read_text(), Loader=UniqueKeyLoader)

    assert isinstance(data, dict)


@pytest.mark.parametrize("path", sorted(DASHBOARDS.glob("*.yaml")), ids=_path_name_id)
def test_dashboard_files_do_not_use_unsupported_blueprints(path: Path) -> None:
    """Dashboard examples do not use unsupported Lovelace blueprint metadata."""
    text = path.read_text()

    assert not text.startswith("blueprint:")
    assert "domain: lovelace" not in text


@pytest.mark.parametrize(
    "path",
    [ROOT / "README.md", DASHBOARDS / "README.md"],
    ids=_root_relative_id,
)
def test_dashboard_docs_do_not_link_unsupported_blueprint_imports(path: Path) -> None:
    """Dashboard docs use supported YAML dashboard registration, not blueprint import."""
    text = path.read_text()

    assert "blueprint_import" not in text
    assert "my.home-assistant" not in text
    assert "lovelace.dashboards" in text


@pytest.mark.parametrize("path", _dashboard_files(), ids=_root_relative_id)
def test_dashboard_entity_references_are_known(path: Path) -> None:
    """Dashboard entity IDs match defined integration sensors."""
    known_entities = _known_dashboard_entities()
    entities = set(DASHBOARD_ENTITY_RE.findall(path.read_text()))

    assert entities <= known_entities


@pytest.mark.parametrize("path", _dashboard_files(), ids=_root_relative_id)
def test_dashboards_do_not_reference_disabled_default_entities(path: Path) -> None:
    """Dashboard examples avoid disabled-by-default entities that render as missing."""
    disabled_entities = _disabled_default_dashboard_entities()
    entities = set(DASHBOARD_ENTITY_RE.findall(path.read_text()))

    assert not (entities & disabled_entities)


@pytest.mark.parametrize("filename", CURATED_DASHBOARDS)
def test_installed_curated_dashboards_match_root_examples(filename: str) -> None:
    """Runtime notification dashboards stay synchronized with root examples."""
    assert (INSTALLED_DASHBOARDS / filename).read_text() == (
        DASHBOARDS / filename
    ).read_text()


@pytest.mark.parametrize(
    "translation_path",
    sorted(TRANSLATIONS.glob("*.json")),
    ids=_path_name_id,
)
def test_translation_placeholders_match_base_strings(translation_path: Path) -> None:
    """Translated strings keep the same placeholders as the base strings."""
    base_leaves = _string_leaves(_load_json(INTEGRATION / "strings.json"))
    translation_leaves = _string_leaves(_load_json(translation_path))

    for path, base_value in base_leaves.items():
        if path not in translation_leaves:
            continue
        assert _placeholders(translation_leaves[path]) == _placeholders(base_value), (
            path
        )
