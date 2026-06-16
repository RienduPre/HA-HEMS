"""DataUpdateCoordinator for HA-HEMS."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, UPDATE_INTERVAL_SECONDS
from .discovery.solar import discover_solar
from .discovery.grid import discover_grid
from .discovery.battery import discover_battery
from .discovery.ev_charger import discover_ev_chargers
from .discovery.tariff import discover_tariff

_LOGGER = logging.getLogger(__name__)


class HEMSCoordinator(DataUpdateCoordinator):
    """Manages polling and state for all HEMS devices."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self.entry = entry
        self.solar = None
        self.grid = None
        self.battery = None
        self.ev_chargers = []
        self.tariff = None
        self._manager = None  # set after setup

    def set_manager(self, manager) -> None:
        """Register the HEMSManager so coordinator can trigger control."""
        self._manager = manager

    async def async_discover_devices(self) -> None:
        """Run discovery for all device types."""
        self.solar = await discover_solar(self.hass, self.entry)
        self.grid = await discover_grid(self.hass, self.entry)
        self.battery = await discover_battery(self.hass, self.entry)
        self.ev_chargers = await discover_ev_chargers(self.hass, self.entry)
        self.tariff = await discover_tariff(self.hass, self.entry)

    async def _async_update_data(self) -> dict:
        """Fetch latest data, then trigger control evaluation."""
        try:
            data = {}

            if self.solar:
                data["solar_power"] = self._get_state_float(self.solar.power_entity)

            if self.grid:
                data["grid_power"] = self._get_state_float(self.grid.power_entity)

            if self.battery:
                data["battery_soc"] = self._get_state_float(self.battery.soc_entity)
                data["battery_power"] = self._get_state_float(self.battery.power_entity)

            if self.tariff:
                data["current_tariff"] = self._get_state_float(self.tariff.price_entity)

            data["ev_chargers"] = [
                {
                    "name": ev.name,
                    "power": self._get_state_float(ev.power_entity),
                    "charging": self._get_state_bool(ev.charging_switch),
                }
                for ev in self.ev_chargers
            ]

            # Trigger control logic after every data refresh
            if self._manager:
                await self._manager.async_evaluate()

            return data

        except Exception as err:
            raise UpdateFailed(f"Error updating HEMS data: {err}") from err

    def _get_state_float(self, entity_id: str | None) -> float | None:
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable"):
            return None
        try:
            return float(state.state)
        except ValueError:
            return None

    def _get_state_bool(self, entity_id: str | None) -> bool | None:
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None:
            return None
        return state.state == "on"
