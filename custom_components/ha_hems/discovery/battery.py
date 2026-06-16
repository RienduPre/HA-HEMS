"""Discover home battery entities."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er

from ..const import CONF_BATTERY_SOC_ENTITY, CONF_BATTERY_POWER_ENTITY

_LOGGER = logging.getLogger(__name__)


@dataclass
class BatteryDevice:
    """Represents a discovered home battery."""
    soc_entity: str     # % state of charge
    power_entity: str   # W, positive = charging, negative = discharging
    name: str


async def discover_battery(hass: HomeAssistant, entry: ConfigEntry) -> BatteryDevice | None:
    """Find home battery SOC and power entities.

    Platforms: sessy, powervault, solis, solax, huawei_solar, foxess, goodwe
    """
    manual_soc = entry.data.get(CONF_BATTERY_SOC_ENTITY)
    manual_power = entry.data.get(CONF_BATTERY_POWER_ENTITY)
    if manual_soc and manual_power:
        return BatteryDevice(soc_entity=manual_soc, power_entity=manual_power, name="Battery (manual)")

    registry = er.async_get(hass)

    battery_platforms = {
        "sessy", "powervault", "solis", "solax", "huawei_solar",
        "foxess", "goodwe", "pylontech", "byd_bess",
    }

    soc_candidates = []
    power_candidates = []

    for entity in registry.entities.values():
        if entity.domain != "sensor":
            continue
        if entity.disabled_by:
            continue

        platform = entity.platform or ""
        uid = (entity.unique_id or "").lower()
        name = (entity.original_name or "").lower()
        dc = entity.device_class or entity.original_device_class

        is_battery_platform = platform in battery_platforms
        has_battery_hint = any(kw in uid or kw in name for kw in ("battery", "batterij", "accu", "bess", "storage"))

        if dc == SensorDeviceClass.BATTERY and (is_battery_platform or has_battery_hint):
            tier = 0 if is_battery_platform else 1
            soc_candidates.append((tier, entity.entity_id, entity.original_name or entity.entity_id))

        if dc == SensorDeviceClass.POWER and (is_battery_platform or has_battery_hint):
            tier = 0 if is_battery_platform else 1
            power_candidates.append((tier, entity.entity_id, entity.original_name or entity.entity_id))

    if not soc_candidates or not power_candidates:
        _LOGGER.info("Battery discovery: no battery found (this is OK if you have no home battery)")
        return None

    soc_candidates.sort(key=lambda x: x[0])
    power_candidates.sort(key=lambda x: x[0])

    soc = soc_candidates[0]
    power = power_candidates[0]
    _LOGGER.info("Battery discovery: SOC=%s, power=%s", soc[1], power[1])
    return BatteryDevice(soc_entity=soc[1], power_entity=power[1], name=soc[2])
