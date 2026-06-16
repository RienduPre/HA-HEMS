"""Sensor platform for HA-HEMS."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower, UnitOfEnergy, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HEMSCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class HEMSSensorDescription(SensorEntityDescription):
    """Describes a HA-HEMS sensor."""
    data_key: str = ""
    unit: str | None = None


SENSOR_DESCRIPTIONS: tuple[HEMSSensorDescription, ...] = (
    HEMSSensorDescription(
        key="solar_power",
        data_key="solar_power",
        name="Solar Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-power",
    ),
    HEMSSensorDescription(
        key="grid_power",
        data_key="grid_power",
        name="Grid Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:transmission-tower",
    ),
    HEMSSensorDescription(
        key="battery_soc",
        data_key="battery_soc",
        name="Battery SOC",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery",
    ),
    HEMSSensorDescription(
        key="battery_power",
        data_key="battery_power",
        name="Battery Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-charging",
    ),
    HEMSSensorDescription(
        key="current_tariff",
        data_key="current_tariff",
        name="Current Electricity Tariff",
        native_unit_of_measurement="EUR/kWh",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:currency-eur",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HA-HEMS sensors."""
    coordinator: HEMSCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[HEMSSensor] = []

    for description in SENSOR_DESCRIPTIONS:
        # Only add sensor if the underlying device was discovered
        if description.data_key == "solar_power" and not coordinator.solar:
            continue
        if description.data_key == "grid_power" and not coordinator.grid:
            continue
        if description.data_key in ("battery_soc", "battery_power") and not coordinator.battery:
            continue
        if description.data_key == "current_tariff" and not coordinator.tariff:
            continue
        entities.append(HEMSSensor(coordinator, description))

    # EV charger sensors (one per discovered charger)
    for i, charger in enumerate(coordinator.ev_chargers):
        entities.append(HEMSEVSensor(coordinator, charger, i))

    async_add_entities(entities)


class HEMSSensor(CoordinatorEntity, SensorEntity):
    """A HA-HEMS sensor entity."""

    entity_description: HEMSSensorDescription

    def __init__(self, coordinator: HEMSCoordinator, description: HEMSSensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"ha_hems_{description.key}"
        self._attr_name = f"HEMS {description.name}"

    @property
    def native_value(self) -> Any:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get(self.entity_description.data_key)


class HEMSEVSensor(CoordinatorEntity, SensorEntity):
    """Power sensor for a discovered EV charger."""

    def __init__(self, coordinator: HEMSCoordinator, charger, index: int) -> None:
        super().__init__(coordinator)
        self._charger = charger
        self._index = index
        self._attr_unique_id = f"ha_hems_ev_{index}_power"
        self._attr_name = f"HEMS EV {charger.name} Power"
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:ev-station"

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        ev_list = self.coordinator.data.get("ev_chargers", [])
        if self._index < len(ev_list):
            return ev_list[self._index].get("power")
        return None
