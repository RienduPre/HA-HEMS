"""Central control manager — multi-device aware."""
from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from .ev_charger import EVChargerController
from .battery import BatteryController
from .scheduler import HEMSScheduler

_LOGGER = logging.getLogger(__name__)


class HEMSManager:
    """Orchestrates all HEMS control logic for multiple devices."""

    def __init__(self, hass: HomeAssistant, coordinator) -> None:
        self.hass = hass
        self.coordinator = coordinator
        self.scheduler = HEMSScheduler(hass, coordinator)
        self.ev_controllers: list[EVChargerController] = []
        self.battery_controllers: list[BatteryController] = []

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
