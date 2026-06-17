"""Discover EV chargers — one charger per physical device, preferring the aggregate power sensor."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er

_LOGGER = logging.getLogger(__name__)

EV_PLATFORMS = {"wallbox", "easee", "evcc", "zaptec", "alfen", "ocpp", "chargeamps"}
EV_KEYWORDS = ("charger", "wallbox", "laadpaal", "ev", "charging", "laden", "charge")
SWITCH_KEYWORDS = ("charging_enable", "enable", "laden", "charge", "start")
CURRENT_KEYWORDS = ("current", "ampere", "stroom", "max_charging", "max_current")

# Per-phase / sub-metric power sensors that should NEVER be picked over
# the aggregate — these caused the integration to report 1/3rd of
# actual charging power in earlier versions.
POWER_SUBMETRIC_EXCLUDE = (
    "_l1", "_l2", "_l3", "phase", "power_boost", "boost_l",
)


@dataclass
class EVChargerDevice:
    """Represents a single EV charger (one physical unit)."""
    name: str
    power_entity: str
    charging_switch: str
    max_current_entity: str | None = None


async def discover_ev_chargers(hass: HomeAssistant, entry: ConfigEntry) -> list[EVChargerDevice]:
    """Find all EV chargers. Returns one EVChargerDevice per physical charger.

    For the power sensor, explicitly prefers an aggregate/total power
    reading over per-phase (L1/L2/L3) or sub-metric (power boost) sensors
    on the same device — picking a per-phase sensor silently under-reports
    charging power by roughly 2/3.
    """
    manual = entry.data.get("ev_chargers")
    if manual:
        return [
            EVChargerDevice(
                name=c.get("name", f"EV Charger {i+1}"),
                power_entity=c["power"],
                charging_switch=c["switch"],
                max_current_entity=c.get("max_current"),
            )
            for i, c in enumerate(manual)
        ]

    registry = er.async_get(hass)

    # device_id -> list of (is_submetric, entity_id, name) power candidates
    power_candidates_by_device: dict[str, list[tuple[bool, str, str]]] = {}
    switch_by_device: dict[str, str] = {}
    current_by_device: dict[str, str] = {}

    for entity in registry.entities.values():
        if entity.disabled_by:
            continue

        platform = entity.platform or ""
        uid = (entity.unique_id or "").lower()
        name = (entity.original_name or "").lower()
        eid = entity.entity_id.lower()
        device_id = entity.device_id or ""
        dc = entity.device_class or entity.original_device_class

        is_ev_platform = platform in EV_PLATFORMS
        has_ev_hint = any(kw in uid or kw in name for kw in EV_KEYWORDS)

        if not (is_ev_platform or has_ev_hint) or not device_id:
            continue

        if entity.domain == "sensor" and dc == SensorDeviceClass.POWER:
            is_submetric = any(sub in uid or sub in eid for sub in POWER_SUBMETRIC_EXCLUDE)
            power_candidates_by_device.setdefault(device_id, []).append(
                (is_submetric, entity.entity_id, entity.original_name or entity.entity_id)
            )

        elif entity.domain == "switch" and any(kw in name or kw in uid for kw in SWITCH_KEYWORDS):
            if device_id and device_id not in switch_by_device:
                switch_by_device[device_id] = entity.entity_id

        elif entity.domain == "number" and any(kw in name or kw in uid for kw in CURRENT_KEYWORDS):
            if device_id and device_id not in current_by_device:
                current_by_device[device_id] = entity.entity_id

    chargers = []
    for device_id, candidates in power_candidates_by_device.items():
        # Prefer non-submetric (aggregate) sensors; among those, shortest
        # entity_id wins (aggregate sensors have simpler names than
        # sub-metrics like 'charging_power_l3').
        candidates.sort(key=lambda c: (c[0], len(c[1])))
        _, power_entity, name = candidates[0]

        switch = switch_by_device.get(device_id)
        if not switch:
            _LOGGER.warning("EV charger '%s': no charging switch found, skipping", name)
            continue

        chargers.append(EVChargerDevice(
            name=name,
            power_entity=power_entity,
            charging_switch=switch,
            max_current_entity=current_by_device.get(device_id),
        ))
        _LOGGER.info("EV charger discovered: %s (power=%s, switch=%s)", name, power_entity, switch)

    _LOGGER.info("EV discovery: found %d charger(s)", len(chargers))
    return chargers
