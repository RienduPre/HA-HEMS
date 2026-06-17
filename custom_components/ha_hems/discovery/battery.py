"""Discover home battery entities — one SOC+power pair per physical battery."""
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

BATTERY_KEYWORDS_STRICT = ("sessy", "batterij", "battery", "accu", "bess")

EXCLUDE_SUBSTRINGS = (
    "hems_",
    "heat_pump", "heatpump", "warmtepomp",
    "laadpaal", "wallbox", "ev_", "charger", "charging",
    "grid", "net_naar", "netto",
)


@dataclass
class BatteryDevice:
    """Represents a single home battery unit."""
    soc_entity: str
    power_entity: str
    name: str


def _is_excluded(uid: str, name: str, entity_id: str) -> bool:
    haystack = f"{uid} {name} {entity_id}".lower()
    return any(bad in haystack for bad in EXCLUDE_SUBSTRINGS)


async def discover_battery(hass: HomeAssistant, entry: ConfigEntry) -> list[BatteryDevice]:
    """Find all home battery units, grouped strictly by device_id.

    A standalone (no device_id) SOC or power sensor is NOT paired with
    another standalone sensor — that caused incorrect cross-pairing
    between unrelated SOC/power sensors in earlier versions. Only
    sensors sharing the same physical device_id are combined.
    """
    manual = entry.data.get("battery_devices")
    if manual:
        return [
            BatteryDevice(soc_entity=b["soc"], power_entity=b["power"], name=f"Battery {i+1} (manual)")
            for i, b in enumerate(manual)
        ]

    registry = er.async_get(hass)

    soc_by_device: dict[str, tuple[int, str, str]] = {}
    power_by_device: dict[str, tuple[int, str]] = {}

    for entity in registry.entities.values():
        if entity.domain != "sensor" or entity.disabled_by:
            continue

        platform = entity.platform or ""
        uid = (entity.unique_id or "").lower()
        name = (entity.original_name or "").lower()
        eid = entity.entity_id
        dc = entity.device_class or entity.original_device_class
        device_id = entity.device_id

        if not device_id:
            continue  # require a real device grouping to avoid cross-pairing unrelated sensors

        if _is_excluded(uid, name, eid):
            continue

        is_battery_platform = platform in BATTERY_PLATFORMS
        has_battery_hint = any(kw in uid or kw in name for kw in BATTERY_KEYWORDS_STRICT)

        if not (is_battery_platform or has_battery_hint):
            continue

        tier = 0 if is_battery_platform else 1

        if dc == SensorDeviceClass.BATTERY:
            existing = soc_by_device.get(device_id)
            if existing is None or tier < existing[0]:
                soc_by_device[device_id] = (tier, eid, entity.original_name or eid)

        if dc == SensorDeviceClass.POWER:
            existing = power_by_device.get(device_id)
            if existing is None or tier < existing[0]:
                power_by_device[device_id] = (tier, eid)

    batteries = []
    for device_id, (_, soc_eid, soc_name) in soc_by_device.items():
        power_info = power_by_device.get(device_id)
        if not power_info:
            _LOGGER.warning("Battery '%s': no power entity on same device, skipping", soc_name)
            continue
        batteries.append(BatteryDevice(soc_entity=soc_eid, power_entity=power_info[1], name=soc_name))

    _LOGGER.info("Battery discovery: found %d unit(s)", len(batteries))
    return batteries
