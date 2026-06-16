"""Discover grid power/energy entities."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er

from ..const import CONF_GRID_ENTITY

_LOGGER = logging.getLogger(__name__)


@dataclass
class GridDevice:
    """Represents discovered grid connection entities."""
    power_entity: str       # W, positive = import, negative = export
    name: str


async def discover_grid(hass: HomeAssistant, entry: ConfigEntry) -> GridDevice | None:
    """Find the best grid power entity.

    Priority:
    1. Manually configured entity
    2. Platform: dsmr, dsmr_reader, p1_monitor, tibber_pulse, ztatz, homewizard
    3. Name/uid hints: 'net', 'grid', 'meter', 'p1', 'dsmr', 'slimme meter'
    """
    manual = entry.data.get(CONF_GRID_ENTITY)
    if manual:
        _LOGGER.debug("Grid: using manually configured entity %s", manual)
        return GridDevice(power_entity=manual, name="Grid (manual)")

    registry = er.async_get(hass)

    grid_platforms = {
        "dsmr", "dsmr_reader", "p1_monitor", "tibber",
        "homewizard", "ztatz", "youless", "easyenergy",
    }

    candidates = []

    for entity in registry.entities.values():
        if entity.domain != "sensor":
            continue
        if entity.device_class != SensorDeviceClass.POWER and entity.original_device_class != SensorDeviceClass.POWER:
            continue
        if entity.disabled_by:
            continue

        platform = entity.platform or ""
        uid = (entity.unique_id or "").lower()
        name = (entity.original_name or "").lower()

        if platform in grid_platforms:
            candidates.append((0, entity.entity_id, entity.original_name or entity.entity_id))
            continue

        if any(kw in uid or kw in name for kw in ("net", "grid", "meter", "p1", "dsmr", "slimme", "levering", "afname")):
            candidates.append((1, entity.entity_id, entity.original_name or entity.entity_id))

    if not candidates:
        _LOGGER.warning("Grid discovery: no candidate found")
        return None

    candidates.sort(key=lambda x: x[0])
    best = candidates[0]
    _LOGGER.info("Grid discovery: selected %s (confidence tier %d)", best[1], best[0])
    return GridDevice(power_entity=best[1], name=best[2])
