"""Sensor platform for HA-HEMS — multi-device aware."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HEMSCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up all HA-HEMS sensor entities."""
    coordinator: HEMSCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []

    # --- Totals ---
    if coordinator.solar_devices:
        entities.append(HEMSTotalSensor(
            coordinator, "solar_power_total", "Solar Power Total",
            UnitOfPower.WATT, SensorDeviceClass.POWER, "mdi:solar-power-variant",
        ))
    if coordinator.grid_devices:
        entities.append(HEMSTotalSensor(
            coordinator, "grid_power_total", "Grid Power Total",
            UnitOfPower.WATT, SensorDeviceClass.POWER, "mdi:transmission-tower",
        ))
    if coordinator.battery_devices:
        entities.append(HEMSTotalSensor(
            coordinator, "battery_power_total", "Battery Power Total",
            UnitOfPower.WATT, SensorDeviceClass.POWER, "mdi:battery-charging",
        ))
        entities.append(HEMSTotalSensor(
            coordinator, "battery_soc_avg", "Battery SOC Average",
            PERCENTAGE, SensorDeviceClass.BATTERY, "mdi:battery",
        ))
    if coordinator.ev_chargers:
        entities.append(HEMSTotalSensor(
            coordinator, "ev_power_total", "EV Charging Power Total",
            UnitOfPower.WATT, SensorDeviceClass.POWER, "mdi:ev-station",
        ))
    if coordinator.tariff:
        entities.append(HEMSTotalSensor(
            coordinator, "current_tariff", "Current Electricity Tariff",
            "EUR/kWh", SensorDeviceClass.MONETARY, "mdi:currency-eur",
        ))

    # --- Per solar inverter ---
    for i, device in enumerate(coordinator.solar_devices):
        entities.append(HEMSDeviceListSensor(
            coordinator, "solar_devices", i, "power",
            f"Solar {device.name}",
            UnitOfPower.WATT, SensorDeviceClass.POWER, "mdi:solar-power",
        ))

    # --- Per grid meter ---
    for i, device in enumerate(coordinator.grid_devices):
        entities.append(HEMSDeviceListSensor(
            coordinator, "grid_devices", i, "power",
            f"Grid {device.name}",
            UnitOfPower.WATT, SensorDeviceClass.POWER, "mdi:meter-electric",
        ))

    # --- Per battery ---
    for i, device in enumerate(coordinator.battery_devices):
        entities.append(HEMSDeviceListSensor(
            coordinator, "battery_devices", i, "soc",
            f"Battery {device.name} SOC",
            PERCENTAGE, SensorDeviceClass.BATTERY, "mdi:battery",
        ))
        entities.append(HEMSDeviceListSensor(
            coordinator, "battery_devices", i, "power",
            f"Battery {device.name} Power",
            UnitOfPower.WATT, SensorDeviceClass.POWER, "mdi:battery-charging",
        ))

    # --- Per EV charger ---
    for i, device in enumerate(coordinator.ev_chargers):
        entities.append(HEMSDeviceListSensor(
            coordinator, "ev_chargers", i, "power",
            f"EV {device.name} Power",
            UnitOfPower.WATT, SensorDeviceClass.POWER, "mdi:ev-station",
        ))

    async_add_entities(entities)


class HEMSTotalSensor(CoordinatorEntity, SensorEntity):
    """A sensor showing a total/aggregate value."""

    def __init__(self, coordinator, data_key, name, unit, device_class, icon) -> None:
        super().__init__(coordinator)
        self._data_key = data_key
        self._attr_unique_id = f"ha_hems_{data_key}"
        self._attr_name = f"HEMS {name}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = icon

    @property
    def native_value(self) -> Any:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get(self._data_key)


class HEMSDeviceListSensor(CoordinatorEntity, SensorEntity):
    """A sensor for a specific value from a device in a list."""

    def __init__(self, coordinator, list_key, index, value_key, name, unit, device_class, icon) -> None:
        super().__init__(coordinator)
        self._list_key = list_key
        self._index = index
        self._value_key = value_key
        self._attr_unique_id = f"ha_hems_{list_key}_{index}_{value_key}"
        self._attr_name = f"HEMS {name}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = icon

    @property
    def native_value(self) -> Any:
        if not self.coordinator.data:
            return None
        lst = self.coordinator.data.get(self._list_key, [])
        if self._index < len(lst):
            return lst[self._index].get(self._value_key)
        return None
