"""Discover solar (PV) power entities."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er

from ..const import CONF_SOLAR_ENTITY

_LOGGER = logging.getLogger(__name__)


@dataclass
class SolarDevice:
    """Represents a discovered solar inverter/panel entity."""
    power_entity: str
    name: str


async def discover_solar(hass: HomeAssistant, entry: ConfigEntry) -> SolarDevice | None:
    """Find the best solar power entity.

    Priority:
    1. Manually configured entity in config entry
    2. Sensor with device_class=power + platform=growatt/solarlog/fronius/solaredge/goodwe
    3. Sensor with device_class=power and 'pv' or 'solar' in unique_id or name
    """
    # 1. Manual override
    manual = entry.data.get(CONF_SOLAR_ENTITY)
    if manual:
        _LOGGER.debug("Solar: using manually configured entity %s", manual)
        return SolarDevice(power_entity=manual, name="Solar (manual)")

    registry = er.async_get(hass)
    
    # Known solar inverter platforms
    solar_platforms = {
        "growatt_local", "growatt_server", "solarlog", "fronius",
        "solaredge", "goodwe", "huawei_solar", "sma", "enphase_envoy",
        "grott",  # Growatt via Grott add-on (used at Casa du Pré)
    }

    candidates = []

    for entry_entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        pass  # skip own entities

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

        # Platform match — highest confidence
        if platform in solar_platforms:
            candidates.append((0, entity.entity_id, entity.original_name or entity.entity_id))
            continue

        # Name/unique_id hint — medium confidence
        if any(kw in uid or kw in name for kw in ("pv", "solar", "inverter", "paneel", "zonnepaneel")):
            candidates.append((1, entity.entity_id, entity.original_name or entity.entity_id))

    if not candidates:
        _LOGGER.warning("Solar discovery: no candidate found")
        return None

    candidates.sort(key=lambda x: x[0])
    best = candidates[0]
    _LOGGER.info("Solar discovery: selected %s (confidence tier %d)", best[1], best[0])
    return SolarDevice(power_entity=best[1], name=best[2])
