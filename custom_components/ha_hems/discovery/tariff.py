"""Discover electricity tariff/price entities."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er

from ..const import CONF_TARIFF_ENTITY

_LOGGER = logging.getLogger(__name__)


@dataclass
class TariffDevice:
    """Represents the electricity price source."""
    price_entity: str   # €/kWh current price
    name: str
    is_dynamic: bool = True


async def discover_tariff(hass: HomeAssistant, entry: ConfigEntry) -> TariffDevice | None:
    """Find the electricity price entity.

    Priority:
    1. Manually configured entity
    2. Platform: tibber, nordpool, entsoe, energyzero, easyenergy
    3. Sensor with device_class=monetary + price/tariff hint
    """
    manual = entry.data.get(CONF_TARIFF_ENTITY)
    if manual:
        return TariffDevice(price_entity=manual, name="Tariff (manual)")

    registry = er.async_get(hass)

    tariff_platforms = {
        "tibber", "nordpool", "entsoe", "energyzero",
        "easyenergy", "awattar", "epex_spot",
    }

    candidates = []

    for entity in registry.entities.values():
        if entity.domain != "sensor":
            continue
        if entity.disabled_by:
            continue

        platform = entity.platform or ""
        uid = (entity.unique_id or "").lower()
        name = (entity.original_name or "").lower()
        dc = entity.device_class or entity.original_device_class

        if platform in tariff_platforms:
            candidates.append((0, entity.entity_id, entity.original_name or entity.entity_id, True))
            continue

        if dc in (SensorDeviceClass.MONETARY, "monetary"):
            if any(kw in uid or kw in name for kw in ("price", "tariff", "prijs", "tarief", "rate", "kwh")):
                candidates.append((1, entity.entity_id, entity.original_name or entity.entity_id, True))

    if not candidates:
        _LOGGER.warning("Tariff discovery: no price entity found")
        return None

    candidates.sort(key=lambda x: x[0])
    best = candidates[0]
    _LOGGER.info("Tariff discovery: selected %s", best[1])
    return TariffDevice(price_entity=best[1], name=best[2], is_dynamic=best[3])
