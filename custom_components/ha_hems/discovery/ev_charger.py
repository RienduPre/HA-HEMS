"""Discover EV chargers — supports multiple chargers and multiple cars."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er

_LOGGER = logging.getLogger(__name__)

EV_PLATFORMS = {"wallbox", "easee", "evcc", "zaptec", "alfen", "ocpp", "chargeamps"}
# Wallbox installs are often MQTT-bridged rather than using the native
# 'wallbox' platform, so keyword matching on name/unique_id is required too.
EV_KEYWORDS = ("charger", "wallbox", "laadpaal", "ev", "charging", "laden", "charge")
SWITCH_KEYWORDS = ("charging_enable", "enable", "laden", "charge", "start")
CURRENT_KEYWORDS = ("current", "ampere", "stroom", "max_charging", "max_current")

# Per-phase / sub-metric suffixes that should be deprioritized in favor of
# the single aggregate power sensor (e.g. prefer 'charging_power' over
# 'charging_power_l1' / '_l2' / '_l3').
PER_PHASE_SUFFIXES = ("_l1", "_l2", "_l3", "_phase1", "_phase2", "_phase3")

EXCLUDE_SUBSTRINGS = (
    "hems_",  # avoid self-matching our own previously created entities
)


@dataclass
class EVChargerDevice:
    """Represents a single EV charger (one physical unit)."""
    name: str
    power_entity: str
    charging_switch: str
    max_current_entity: str | None = None
    # Future: car_soc_entity per connected car


def _is_excluded(uid: str, name: str, entity_id: str) -> bool:
    haystack = f"{uid} {name} {entity_id}".lower()
    return any(bad in haystack for bad in EXCLUDE_SUBSTRINGS)


def _is_per_phase(uid: str, name: str, entity_id: str) -> bool:
    haystack = f"{uid} {name} {entity_id}".lower()
    return any(suffix in haystack for suffix in PER_PHASE_SUFFIXES)


async def discover_ev_chargers(hass: HomeAssistant, entry: ConfigEntry) -> list[EVChargerDevice]:
    """Find all EV chargers. Returns one EVChargerDevice per physical charger.

    Within a single device, the aggregate power sensor (e.g.
    'charging_power') is preferred over per-phase sub-metrics
    (e.g. 'charging_power_l3'), which previously caused the wrong
    (much lower) sensor to be picked for charger control decisions.
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

    # device_id -> (is_per_phase, entity_id, name) — prefer non-per-phase (tier 0)
    power_by_device: dict[str, tuple[bool, str, str]] = {}
    switch_by_device: dict[str, str] = {}
    current_by_device: dict[str, str] = {}

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

        is_ev_platform = platform in EV_PLATFORMS
        has_ev_hint = any(kw in uid or kw in name for kw in EV_KEYWORDS)

        if not (is_ev_platform or has_ev_hint):
            continue

        if entity.domain == "sensor" and dc == SensorDeviceClass.POWER:
            if not device_id:
                continue
            per_phase = _is_per_phase(uid, name, eid)
            existing = power_by_device.get(device_id)
            # Prefer aggregate (per_phase=False) over per-phase (per_phase=True)
            if existing is None or (existing[0] and not per_phase):
                power_by_device[device_id] = (per_phase, eid, entity.original_name or eid)

        elif entity.domain == "switch" and any(kw in name or kw in uid for kw in SWITCH_KEYWORDS):
            if device_id and device_id not in switch_by_device:
                switch_by_device[device_id] = eid

        elif entity.domain == "number" and any(kw in name or kw in uid for kw in CURRENT_KEYWORDS):
            if device_id and device_id not in current_by_device:
                current_by_device[device_id] = eid

    chargers = []
    for device_id, (_, power_entity, name) in power_by_device.items():
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
