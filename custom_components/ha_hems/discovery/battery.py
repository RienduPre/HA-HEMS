"""Discover home battery entities — supports multiple batteries."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er

_LOGGER = logging.getLogger(__name__)

BATTERY_PLATFORMS = {
    "sessy", "powervault", "solis", "solax", "huawei_solar",
    "foxess", "goodwe", "pylontech", "byd_bess",
}

BATTERY_KEYWORDS = ("battery", "batterij", "accu", "bess", "storage")


@dataclass
class BatteryDevice:
    """Represents a single home battery unit."""
    soc_entity: str
    power_entity: str
    name: str


async def discover_battery(hass: HomeAssistant, entry: ConfigEntry) -> list[BatteryDevice]:
    """Find all home battery units."""
    manual = entry.data.get("battery_devices")  # list of {soc, power}
    if manual:
        return [
            BatteryDevice(soc_entity=b["soc"], power_entity=b["power"], name=f"Battery {i+1} (manual)")
            for i, b in enumerate(manual)
        ]

    registry = er.async_get(hass)

    # Group by device_id: each physical battery has one SOC + one power entity
    soc_by_device: dict[str, tuple[str, str, int]] = {}    # device_id -> (entity_id, name, tier)
    power_by_device: dict[str, tuple[str, int]] = {}       # device_id -> (entity_id, tier)

    for entity in registry.entities.values():
        if entity.domain != "sensor" or entity.disabled_by:
            continue

        platform = entity.platform or ""
        uid = (entity.unique_id or "").lower()
        name = (entity.original_name or "").lower()
        dc = entity.device_class or entity.original_device_class
        device_id = entity.device_id or entity.entity_id  # fallback grouping

        is_battery_platform = platform in BATTERY_PLATFORMS
        has_battery_hint = any(kw in uid or kw in name for kw in BATTERY_KEYWORDS)

        if not (is_battery_platform or has_battery_hint):
            continue

        tier = 0 if is_battery_platform else 1

        if dc == SensorDeviceClass.BATTERY:
            if device_id not in soc_by_device or tier < soc_by_device[device_id][2]:
                soc_by_device[device_id] = (entity.entity_id, entity.original_name or entity.entity_id, tier)

        if dc == SensorDeviceClass.POWER:
            if device_id not in power_by_device or tier < power_by_device[device_id][1]:
                power_by_device[device_id] = (entity.entity_id, tier)

    batteries = []
    for device_id, (soc_eid, soc_name, _) in soc_by_device.items():
        power_info = power_by_device.get(device_id)
        if not power_info:
            _LOGGER.warning("Battery %s: no power entity found, skipping", soc_name)
            continue
        batteries.append(BatteryDevice(
            soc_entity=soc_eid,
            power_entity=power_info[0],
            name=soc_name,
        ))

    _LOGGER.info("Battery discovery: found %d unit(s)", len(batteries))
    return batteries
