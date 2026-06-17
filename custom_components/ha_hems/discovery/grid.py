"""Discover grid power entities — supports multiple physically distinct meters."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er

_LOGGER = logging.getLogger(__name__)

GRID_PLATFORMS = {
    "dsmr", "dsmr_reader", "p1_monitor", "tibber",
    "homewizard", "ztatz", "youless", "easyenergy",
}

# Strict keywords for actual grid/meter entities. Deliberately narrow —
# generic words like "net" or "power" alone caused false positives on
# heat pump sensors, SEM template sensors, and other unrelated power readings.
GRID_KEYWORDS_STRICT = (
    "p1_meter", "p1 meter", "smart_meter", "slimme meter", "slimmemeter",
    "dsmr", "netimport", "netexport", "netvermogen", "grid_active_power",
    "grid_power", "meter_power",
)

# Hard excludes: things that should NEVER be picked as the grid sensor,
# even if a loose keyword would otherwise match.
EXCLUDE_SUBSTRINGS = (
    "hems_",            # our own previously-created entities (avoid self-matching on reload)
    "heat_pump", "heatpump", "warmtepomp", "outdoor_unit", "calculated_power",
    "laadpaal", "wallbox", "ev_", "charger", "charging",
    "net_naar", "netto",  # SEM template sensors like "Net naar EV/Huis/Batterij"
    "gemiddeld", "max_power", "min_power",  # aggregated/derived stats, not live meter readings
)


@dataclass
class GridDevice:
    """Represents a single grid connection/meter."""
    power_entity: str
    name: str


def _is_excluded(uid: str, name: str, entity_id: str) -> bool:
    haystack = f"{uid} {name} {entity_id}".lower()
    return any(bad in haystack for bad in EXCLUDE_SUBSTRINGS)


async def discover_grid(hass: HomeAssistant, entry: ConfigEntry) -> list[GridDevice]:
    """Find grid power entities — one per physical meter/device.

    Groups candidates by device_id so a single physical meter (which may
    expose several diagnostic sensors) only contributes once. Picks the
    single best (lowest-tier) entity per device.
    """
    manual = entry.data.get("grid_entities")
    if manual:
        return [GridDevice(power_entity=e, name=f"Grid {i+1} (manual)") for i, e in enumerate(manual)]

    registry = er.async_get(hass)

    # device_id -> (tier, entity_id, name)  — keep only the best match per device
    best_per_device: dict[str, tuple[int, str, str]] = {}
    # Entities with no device_id are tracked individually by entity_id
    standalone: dict[str, tuple[int, str, str]] = {}

    for entity in registry.entities.values():
        if entity.domain != "sensor" or entity.disabled_by:
            continue
        dc = entity.device_class or entity.original_device_class
        if dc != SensorDeviceClass.POWER:
            continue

        platform = entity.platform or ""
        uid = (entity.unique_id or "").lower()
        name = (entity.original_name or "").lower()
        eid = entity.entity_id

        if _is_excluded(uid, name, eid):
            continue

        tier: int | None = None
        if platform in GRID_PLATFORMS:
            tier = 0
        elif any(kw in uid or kw in name for kw in GRID_KEYWORDS_STRICT):
            tier = 1

        if tier is None:
            continue

        key = entity.device_id or f"__standalone__{eid}"
        target = best_per_device
        existing = target.get(key)
        if existing is None or tier < existing[0]:
            target[key] = (tier, eid, entity.original_name or eid)

    if not best_per_device:
        _LOGGER.warning("Grid discovery: no meter found")
        return []

    results = sorted(best_per_device.values(), key=lambda x: x[0])
    devices = [GridDevice(power_entity=r[1], name=r[2]) for r in results]
    _LOGGER.info("Grid discovery: found %d meter(s): %s", len(devices), [d.power_entity for d in devices])
    return devices
