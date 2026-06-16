"""Central control manager — ties coordinator, scheduler, and device controllers together."""
from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from .ev_charger import EVChargerController
from .battery import BatteryController
from .scheduler import HEMSScheduler

_LOGGER = logging.getLogger(__name__)


class HEMSManager:
    """Orchestrates all HEMS control logic."""

    def __init__(self, hass: HomeAssistant, coordinator) -> None:
        self.hass = hass
        self.coordinator = coordinator
        self.scheduler = HEMSScheduler(hass, coordinator)
        self.ev_controllers: list[EVChargerController] = []
        self.battery_controller: BatteryController | None = None

    async def async_setup(self) -> None:
        """Initialize controllers after discovery."""
        for charger in self.coordinator.ev_chargers:
            self.ev_controllers.append(EVChargerController(self.hass, charger, self.coordinator))
            _LOGGER.info("HEMSManager: EV controller registered for %s", charger.name)

        if self.coordinator.battery:
            self.battery_controller = BatteryController(self.hass, self.coordinator.battery, self.coordinator)
            _LOGGER.info("HEMSManager: battery controller registered")

    async def async_evaluate(self) -> None:
        """Called on every coordinator update — evaluate schedule and control devices."""
        schedule = self.scheduler.evaluate()
        _LOGGER.debug("HEMSManager schedule: %s", schedule.reason)

        # Apply modes from scheduler
        for ev in self.ev_controllers:
            ev.mode = schedule.ev_mode
            await ev.async_evaluate()

        if self.battery_controller:
            self.battery_controller.mode = schedule.battery_mode
            await self.battery_controller.async_evaluate()
