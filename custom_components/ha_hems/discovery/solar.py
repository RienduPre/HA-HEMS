"""Discover solar (PV) power entities — one per physical inverter/device."""
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

SOLAR_KEYWORDS_STRICT = (
    "pv_power", "solar_power", "inverter_power", "paneel", "zonnepaneel",
    "opwek", "pv1", "pv2", "mppt",
)

EXCLUDE_SUBSTRINGS = (
    "hems_",
    "heat_pump", "heatpump", "warmtepomp", "outdoor_unit",
    "laadpaal", "wallbox", "ev_", "charger", "charging",
    "battery", "batterij", "accu",
    "net_naar", "netto", "grid",
    "gemiddeld", "max_power", "min_power",
)


@dataclass
class SolarDevice:
    """Represents a single solar inverter/string."""
    power_entity: str
    name: str


def _is_excluded(uid: str, name: str, entity_id: str) -> bool:
    haystack = f"{uid} {name} {entity_id}".lower()
    return any(bad in haystack for bad in EXCLUDE_SUBSTRINGS)


async def discover_solar(hass: HomeAssistant, entry: ConfigEntry) -> list[SolarDevice]:
    """Find all solar power entities, one per physical inverter."""
    manual = entry.data.get("solar_entities")
    if manual:
        return [SolarDevice(power_entity=e, name=f"Solar {i+1} (manual)") for i, e in enumerate(manual)]

    registry = er.async_get(hass)
    best_per_device: dict[str, tuple[int, str, str]] = {}

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
        if platform in SOLAR_PLATFORMS:
            tier = 0
        elif any(kw in uid or kw in name for kw in SOLAR_KEYWORDS_STRICT):
            tier = 1

        if tier is None:
            continue

        key = entity.device_id or f"__standalone__{eid}"
        existing = best_per_device.get(key)
        if existing is None or tier < existing[0]:
            best_per_device[key] = (tier, eid, entity.original_name or eid)

    if not best_per_device:
        _LOGGER.warning("Solar discovery: no inverters found")
        return []

    results = sorted(best_per_device.values(), key=lambda x: x[0])
    devices = [SolarDevice(power_entity=r[1], name=r[2]) for r in results]
    _LOGGER.info("Solar discovery: found %d inverter(s): %s", len(devices), [d.power_entity for d in devices])
    return devices
