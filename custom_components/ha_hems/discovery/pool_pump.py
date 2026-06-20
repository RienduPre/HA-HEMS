"""Discover pool pumps and heaters."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er

_LOGGER = logging.getLogger(__name__)

POOL_PLATFORMS = {
    "deye_hybrid", "pool_pump", "pool", "zodiac",
}

POOL_KEYWORDS = (
    "pool", "pump", "pomp", "heating", "warmer", "zwembad",
    "pool_pump", "pool_heater",
)

EXCLUDE_SUBSTRINGS = (
    "hems_",
    "heat_pump", "heatpump", "warmtepomp", "outdoor_unit",
    "laadpaal", "wallbox", "ev_", "charger",
    "battery", "batterij", "solar", "pv",
)


@dataclass
class PoolPumpDevice:
    """Represents a single pool pump/heater."""
    name: str
    power_entity: str | None = None
    switch_entity: str | None = None
    temperature_entity: str | None = None


def _is_excluded(uid: str, name: str, entity_id: str) -> bool:
    haystack = f"{uid} {name} {entity_id}".lower()
    return any(bad in haystack for bad in EXCLUDE_SUBSTRINGS)


async def discover_pool_pumps(hass: HomeAssistant, entry: ConfigEntry) -> list[PoolPumpDevice]:
    """Find pool pumps and heaters."""
    manual = entry.data.get("pool_pumps")
    if manual:
        return [
            PoolPumpDevice(
                name=pp.get("name", f"Pool Pump {i+1}"),
                power_entity=pp.get("power"),
                switch_entity=pp.get("switch"),
                temperature_entity=pp.get("temperature"),
            )
            for i, pp in enumerate(manual)
        ]

    registry = er.async_get(hass)

    power_by_device: dict[str, tuple[int, str, str]] = {}
    switch_by_device: dict[str, str] = {}
    temp_by_device: dict[str, str] = {}

    for entity in registry.entities.values():
        if entity.disabled_by:
            continue

        platform = entity.platform or ""
        uid = (entity.unique_id or "").lower()
        name = (entity.original_name or "").lower()
        eid = entity.entity_id
        device_id = entity.device_id or ""
        dc = entity.device_class or entity.original_device_class

        if _is_excluded(uid, name, eid):
            continue

        is_pool_platform = platform in POOL_PLATFORMS
        has_pool_hint = any(kw in uid or kw in name for kw in POOL_KEYWORDS)

        if not (is_pool_platform or has_pool_hint):
            continue

        # Look for power sensor
        if entity.domain == "sensor" and dc == SensorDeviceClass.POWER:
            if device_id:
                tier = 0 if is_pool_platform else 1
                existing = power_by_device.get(device_id)
                if existing is None or tier < existing[0]:
                    power_by_device[device_id] = (tier, eid, entity.original_name or eid)

        # Look for on/off switch
        elif entity.domain == "switch" and any(kw in uid or kw in name for kw in ("power", "pump", "switch")):
            if device_id and device_id not in switch_by_device:
                switch_by_device[device_id] = eid

        # Look for water temperature
        elif entity.domain == "sensor" and dc == SensorDeviceClass.TEMPERATURE:
            if device_id and any(kw in uid or kw in name for kw in ("temperature", "temp", "water")):
                if device_id not in temp_by_device:
                    temp_by_device[device_id] = eid

    pool_pumps = []
    for device_id, (_, power_entity, name) in power_by_device.items():
        pool_pumps.append(PoolPumpDevice(
            name=name,
            power_entity=power_entity,
            switch_entity=switch_by_device.get(device_id),
            temperature_entity=temp_by_device.get(device_id),
        ))
        _LOGGER.info("Pool pump discovered: %s (power=%s)", name, power_entity)

    _LOGGER.info("Pool pump discovery: found %d unit(s)", len(pool_pumps))
    return pool_pumps
