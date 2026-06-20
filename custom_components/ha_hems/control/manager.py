"""Central control manager — multi-device aware."""
from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from .ev_charger import EVChargerController
from .battery import BatteryController
from .scheduler import HEMSScheduler
from .heat_pump import HeatPumpController
from .ac import ACController
from .pool_pump import PoolPumpController

_LOGGER = logging.getLogger(__name__)


class HEMSManager:
    """Orchestrates all HEMS control logic for multiple devices."""

    def __init__(self, hass: HomeAssistant, coordinator) -> None:
        self.hass = hass
        self.coordinator = coordinator
        self.scheduler = HEMSScheduler(hass, coordinator)
        self.ev_controllers: list[EVChargerController] = []
        self.battery_controllers: list[BatteryController] = []
        self.heat_pump_controllers: list[HeatPumpController] = []
        self.ac_controllers: list[ACController] = []
        self.pool_pump_controllers: list[PoolPumpController] = []

    async def async_setup(self) -> None:
        """Initialize controllers for all discovered devices."""
        for charger in self.coordinator.ev_chargers:
            self.ev_controllers.append(
                EVChargerController(self.hass, charger, self.coordinator)
            )
            _LOGGER.info("HEMSManager: EV controller registered for '%s'", charger.name)

        for battery in self.coordinator.battery_devices:
            self.battery_controllers.append(
                BatteryController(self.hass, battery, self.coordinator)
            )
            _LOGGER.info("HEMSManager: battery controller registered for '%s'", battery.name)

        for heat_pump in self.coordinator.heat_pumps:
            self.heat_pump_controllers.append(
                HeatPumpController(self.hass, heat_pump, self.coordinator)
            )
            _LOGGER.info("HEMSManager: heat pump controller registered for '%s'", heat_pump.name)

        for ac_unit in self.coordinator.ac_units:
            self.ac_controllers.append(
                ACController(self.hass, ac_unit, self.coordinator)
            )
            _LOGGER.info("HEMSManager: AC controller registered for '%s'", ac_unit.name)

        for pool_pump in self.coordinator.pool_pumps:
            self.pool_pump_controllers.append(
                PoolPumpController(self.hass, pool_pump, self.coordinator)
            )
            _LOGGER.info("HEMSManager: pool pump controller registered for '%s'", pool_pump.name)

    async def async_evaluate(self) -> None:
        """Evaluate schedule and control all devices."""
        schedule = self.scheduler.evaluate()
        _LOGGER.debug("HEMSManager: %s", schedule.reason)

        for ev in self.ev_controllers:
            ev.mode = schedule.ev_mode
            await ev.async_evaluate()

        for bat in self.battery_controllers:
            bat.mode = schedule.battery_mode
            await bat.async_evaluate()

        for hp in self.heat_pump_controllers:
            hp.mode = schedule.heat_pump_mode
            await hp.async_evaluate()

        for ac in self.ac_controllers:
            ac.mode = schedule.ac_mode
            await ac.async_evaluate()

        for pp in self.pool_pump_controllers:
            pp.mode = schedule.pool_pump_mode
            await pp.async_evaluate()
