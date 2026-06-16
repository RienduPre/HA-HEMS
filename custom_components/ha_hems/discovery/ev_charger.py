"""Discover EV charger entities."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er

_LOGGER = logging.getLogger(__name__)


@dataclass
class EVChargerDevice:
    """Represents a discovered EV charger."""
    name: str
    power_entity: str           # W actual charging power
    charging_switch: str        # switch to enable/disable charging
    max_current_entity: str | None = None   # number entity for current limit


async def discover_ev_chargers(hass: HomeAssistant, entry: ConfigEntry) -> list[EVChargerDevice]:
    """Find all EV chargers.

    Platforms: wallbox, easee, evcc, zaptec, alfen, ocpp
    Also discovers switch entities that match charging enable patterns.
    """
    registry = er.async_get(hass)

    ev_platforms = {"wallbox", "easee", "evcc", "zaptec", "alfen", "ocpp", "chargeamps"}
    ev_keywords = ("charger", "wallbox", "laadpaal", "ev", "charging", "laden", "charge")

    # Find power sensors per device
    power_by_device: dict[str, tuple[str, str]] = {}   # device_id -> (entity_id, name)
    switch_by_device: dict[str, str] = {}               # device_id -> switch entity_id
    current_by_device: dict[str, str] = {}              # device_id -> number entity_id

    for entity in registry.entities.values():
        if entity.disabled_by:
            continue

        platform = entity.platform or ""
        uid = (entity.unique_id or "").lower()
        name = (entity.original_name or "").lower()
        device_id = entity.device_id or ""

        is_ev_platform = platform in ev_platforms
        has_ev_hint = any(kw in uid or kw in name for kw in ev_keywords)

        if not (is_ev_platform or has_ev_hint):
            continue

        dc = entity.device_class or entity.original_device_class

        if entity.domain == "sensor" and dc == SensorDeviceClass.POWER:
            if device_id and device_id not in power_by_device:
                power_by_device[device_id] = (entity.entity_id, entity.original_name or entity.entity_id)

        elif entity.domain == "switch" and any(kw in name or kw in uid for kw in ("charging_enable", "enable", "laden", "charge")):
            if device_id:
                switch_by_device[device_id] = entity.entity_id

        elif entity.domain == "number" and any(kw in name or kw in uid for kw in ("current", "ampere", "stroom", "max_charging")):
            if device_id:
                current_by_device[device_id] = entity.entity_id

    chargers = []
    for device_id, (power_entity, name) in power_by_device.items():
        switch = switch_by_device.get(device_id)
        if not switch:
            _LOGGER.warning("EV charger %s: no charging switch found, skipping", name)
            continue
        chargers.append(EVChargerDevice(
            name=name,
            power_entity=power_entity,
            charging_switch=switch,
            max_current_entity=current_by_device.get(device_id),
        ))
        _LOGGER.info("EV charger discovered: %s (power=%s, switch=%s)", name, power_entity, switch)

    return chargers
