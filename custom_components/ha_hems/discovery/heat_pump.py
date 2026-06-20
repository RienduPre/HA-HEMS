"""Discover heat pumps with SG Ready support."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er

_LOGGER = logging.getLogger(__name__)

HEAT_PUMP_PLATFORMS = {
    "stiebel_eltron", "thermia", "nibe", "heat_pump", "heatpump",
}

HEAT_PUMP_KEYWORDS = (
    "heat_pump", "heatpump", "warmtepomp", "hp_", "sgready",
    "sg_ready", "sgr", "heating",
)

EXCLUDE_SUBSTRINGS = (
    "hems_",
    "laadpaal", "wallbox", "ev_", "charger", "charging",
    "battery", "batterij", "accu", "solar", "pv",
)


@dataclass
class HeatPumpDevice:
    """Represents a single heat pump with optional SG Ready support."""
    name: str
    power_entity: str | None = None
    sgready_switch: str | None = None
    temperature_entity: str | None = None
    mode_entity: str | None = None


def _is_excluded(uid: str, name: str, entity_id: str) -> bool:
    haystack = f"{uid} {name} {entity_id}".lower()
    return any(bad in haystack for bad in EXCLUDE_SUBSTRINGS)


async def discover_heat_pumps(hass: HomeAssistant, entry: ConfigEntry) -> list[HeatPumpDevice]:
    """Find heat pumps with optional SG Ready support."""
    manual = entry.data.get("heat_pumps")
    if manual:
        return [
            HeatPumpDevice(
                name=hp.get("name", f"Heat Pump {i+1}"),
                power_entity=hp.get("power"),
                sgready_switch=hp.get("sgready_switch"),
                temperature_entity=hp.get("temperature"),
                mode_entity=hp.get("mode"),
            )
            for i, hp in enumerate(manual)
        ]

    registry = er.async_get(hass)

    power_by_device: dict[str, tuple[int, str, str]] = {}
    sgready_by_device: dict[str, str] = {}
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

        is_hp_platform = platform in HEAT_PUMP_PLATFORMS
        has_hp_hint = any(kw in uid or kw in name for kw in HEAT_PUMP_KEYWORDS)

        if not (is_hp_platform or has_hp_hint):
            continue

        # Look for power sensor (current power draw)
        if entity.domain == "sensor" and dc == SensorDeviceClass.POWER:
            if device_id:
                tier = 0 if is_hp_platform else 1
                existing = power_by_device.get(device_id)
                if existing is None or tier < existing[0]:
                    power_by_device[device_id] = (tier, eid, entity.original_name or eid)

        # Look for SG Ready switch (binary/switch for enabling SG Ready mode)
        elif entity.domain in ("binary_sensor", "switch"):
            if device_id and any(kw in uid or kw in name for kw in ("sgready", "sg_ready", "sgr")):
                if device_id not in sgready_by_device:
                    sgready_by_device[device_id] = eid

        # Look for temperature sensor
        elif entity.domain == "sensor" and dc == SensorDeviceClass.TEMPERATURE:
            if device_id and any(kw in uid or kw in name for kw in ("temperature", "temp")):
                if device_id not in temp_by_device:
                    temp_by_device[device_id] = eid

        # Look for mode select (operating mode)
        elif entity.domain == "select" and any(kw in uid or kw in name for kw in ("mode", "operation")):
            if device_id and device_id not in mode_by_device:
                mode_by_device[device_id] = eid

    heat_pumps = []
    for device_id, (_, power_entity, name) in power_by_device.items():
        heat_pumps.append(HeatPumpDevice(
            name=name,
            power_entity=power_entity,
            sgready_switch=sgready_by_device.get(device_id),
            temperature_entity=temp_by_device.get(device_id),
            mode_entity=mode_by_device.get(device_id),
        ))
        _LOGGER.info(
            "Heat pump discovered: %s (power=%s, sg_ready=%s)",
            name, power_entity, sgready_by_device.get(device_id) or "none",
        )

    _LOGGER.info("Heat pump discovery: found %d unit(s)", len(heat_pumps))
    return heat_pumps
