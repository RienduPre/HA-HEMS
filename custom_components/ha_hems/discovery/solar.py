"""Discover solar (PV) power entities — supports multiple inverters."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er

_LOGGER = logging.getLogger(__name__)

SOLAR_PLATFORMS = {
    "growatt_local", "growatt_server", "solarlog", "fronius",
    "solaredge", "goodwe", "huawei_solar", "sma", "enphase_envoy",
    "grott",
}

SOLAR_KEYWORDS = ("pv", "solar", "inverter", "paneel", "zonnepaneel", "opwek")


@dataclass
class SolarDevice:
    """Represents a single solar inverter/string."""
    power_entity: str
    name: str


async def discover_solar(hass: HomeAssistant, entry: ConfigEntry) -> list[SolarDevice]:
    """Find all solar power entities (one per inverter/string)."""
    manual = entry.data.get("solar_entities")  # list of entity_ids
    if manual:
        return [SolarDevice(power_entity=e, name=f"Solar {i+1} (manual)") for i, e in enumerate(manual)]

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

        if platform in SOLAR_PLATFORMS:
            candidates.append((0, eid, entity.original_name or eid))
            seen.add(eid)
        elif any(kw in uid or kw in name for kw in SOLAR_KEYWORDS):
            candidates.append((1, eid, entity.original_name or eid))
            seen.add(eid)

    if not candidates:
        _LOGGER.warning("Solar discovery: no inverters found")
        return []

    candidates.sort(key=lambda x: x[0])
    result = [SolarDevice(power_entity=c[1], name=c[2]) for c in candidates]
    _LOGGER.info("Solar discovery: found %d inverter(s): %s", len(result), [r.power_entity for r in result])
    return result
