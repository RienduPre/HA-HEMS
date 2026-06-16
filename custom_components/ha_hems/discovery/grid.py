"""Discover grid power entities — supports multiple meters (3-phase split etc)."""
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

GRID_KEYWORDS = ("net", "grid", "meter", "p1", "dsmr", "slimme", "levering", "afname")


@dataclass
class GridDevice:
    """Represents a single grid connection/meter."""
    power_entity: str
    name: str


async def discover_grid(hass: HomeAssistant, entry: ConfigEntry) -> list[GridDevice]:
    """Find all grid power entities."""
    manual = entry.data.get("grid_entities")
    if manual:
        return [GridDevice(power_entity=e, name=f"Grid {i+1} (manual)") for i, e in enumerate(manual)]

    registry = er.async_get(hass)
    candidates: list[tuple[int, str, str]] = []
    seen: set[str] = set()

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

        if eid in seen:
            continue

        if platform in GRID_PLATFORMS:
            candidates.append((0, eid, entity.original_name or eid))
            seen.add(eid)
        elif any(kw in uid or kw in name for kw in GRID_KEYWORDS):
            candidates.append((1, eid, entity.original_name or eid))
            seen.add(eid)

    if not candidates:
        _LOGGER.warning("Grid discovery: no meter found")
        return []

    candidates.sort(key=lambda x: x[0])
    result = [GridDevice(power_entity=c[1], name=c[2]) for c in candidates]
    _LOGGER.info("Grid discovery: found %d meter(s): %s", len(result), [r.power_entity for r in result])
    return result
