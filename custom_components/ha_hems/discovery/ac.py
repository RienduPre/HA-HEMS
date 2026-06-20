"""Discover air conditioning units."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er

_LOGGER = logging.getLogger(__name__)

AC_PLATFORMS = {
    "daikin", "fujitsu", "panasonic", "midea", "gree", "toshiba",
}

AC_KEYWORDS = (
    "airco", "air_conditioner", "ac_", "klimaat", "conditioner",
    "cooling", "ac_cooling",
)

EXCLUDE_SUBSTRINGS = (
    "hems_",
    "heat_pump", "heatpump", "warmtepomp",
    "laadpaal", "wallbox", "ev_", "charger",
    "battery", "batterij", "solar", "pv",
)


@dataclass
class ACDevice:
    """Represents a single AC unit."""
    name: str
    power_entity: str | None = None
    switch_entity: str | None = None
    temperature_entity: str | None = None
    mode_entity: str | None = None


def _is_excluded(uid: str, name: str, entity_id: str) -> bool:
    haystack = f"{uid} {name} {entity_id}".lower()
    return any(bad in haystack for bad in EXCLUDE_SUBSTRINGS)


async def discover_ac_units(hass: HomeAssistant, entry: ConfigEntry) -> list[ACDevice]:
    """Find air conditioning units."""
    manual = entry.data.get("ac_units")
    if manual:
        return [
            ACDevice(
                name=ac.get("name", f"AC {i+1}"),
                power_entity=ac.get("power"),
                switch_entity=ac.get("switch"),
                temperature_entity=ac.get("temperature"),
                mode_entity=ac.get("mode"),
            )
            for i, ac in enumerate(manual)
        ]

    registry = er.async_get(hass)

    power_by_device: dict[str, tuple[int, str, str]] = {}
    switch_by_device: dict[str, str] = {}
    temp_by_device: dict[str, str] = {}
    mode_by_device: dict[str, str] = {}

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

        is_ac_platform = platform in AC_PLATFORMS
        has_ac_hint = any(kw in uid or kw in name for kw in AC_KEYWORDS)

        if not (is_ac_platform or has_ac_hint):
            continue

        # Look for power sensor
        if entity.domain == "sensor" and dc == SensorDeviceClass.POWER:
            if device_id:
                tier = 0 if is_ac_platform else 1
                existing = power_by_device.get(device_id)
                if existing is None or tier < existing[0]:
                    power_by_device[device_id] = (tier, eid, entity.original_name or eid)

        # Look for on/off switch
        elif entity.domain == "switch" and any(kw in uid or kw in name for kw in ("power", "switch", "on_off")):
            if device_id and device_id not in switch_by_device:
                switch_by_device[device_id] = eid

        # Look for temperature sensor
        elif entity.domain == "sensor" and dc == SensorDeviceClass.TEMPERATURE:
            if device_id and any(kw in uid or kw in name for kw in ("temperature", "temp", "indoor")):
                if device_id not in temp_by_device:
                    temp_by_device[device_id] = eid

        # Look for mode select
        elif entity.domain == "select" and any(kw in uid or kw in name for kw in ("mode", "operation")):
            if device_id and device_id not in mode_by_device:
                mode_by_device[device_id] = eid

    ac_units = []
    for device_id, (_, power_entity, name) in power_by_device.items():
        ac_units.append(ACDevice(
            name=name,
            power_entity=power_entity,
            switch_entity=switch_by_device.get(device_id),
            temperature_entity=temp_by_device.get(device_id),
            mode_entity=mode_by_device.get(device_id),
        ))
        _LOGGER.info("AC unit discovered: %s (power=%s)", name, power_entity)

    _LOGGER.info("AC discovery: found %d unit(s)", len(ac_units))
    return ac_units
