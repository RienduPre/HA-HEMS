"""DataUpdateCoordinator for HA-HEMS — multi-device aware."""
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
from .discovery.heat_pump import discover_heat_pumps
from .discovery.ac import discover_ac_units
from .discovery.pool_pump import discover_pool_pumps

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
        self.solar_devices: list = []
        self.grid_devices: list = []
        self.battery_devices: list = []
        self.ev_chargers: list = []
        self.heat_pumps: list = []
        self.ac_units: list = []
        self.pool_pumps: list = []
        self.tariff = None
        self._manager = None

    def set_manager(self, manager) -> None:
        self._manager = manager

    async def async_discover_devices(self) -> None:
        """Run discovery for all device types."""
        self.solar_devices = await discover_solar(self.hass, self.entry)
        self.grid_devices = await discover_grid(self.hass, self.entry)
        self.battery_devices = await discover_battery(self.hass, self.entry)
        self.ev_chargers = await discover_ev_chargers(self.hass, self.entry)
        self.heat_pumps = await discover_heat_pumps(self.hass, self.entry)
        self.ac_units = await discover_ac_units(self.hass, self.entry)
        self.pool_pumps = await discover_pool_pumps(self.hass, self.entry)
        self.tariff = await discover_tariff(self.hass, self.entry)

        _LOGGER.info(
            "Discovery complete: %d solar, %d grid, %d battery, %d EV, %d heat pump, %d AC, %d pool pump, tariff=%s",
            len(self.solar_devices), len(self.grid_devices),
            len(self.battery_devices), len(self.ev_chargers),
            len(self.heat_pumps), len(self.ac_units), len(self.pool_pumps),
            self.tariff.price_entity if self.tariff else "none",
        )

    async def _async_update_data(self) -> dict:
        """Fetch latest data from all devices."""
        try:
            data: dict = {}

            # Solar: sum all inverters, keep individual values too
            solar_powers = [
                self._get_state_float(d.power_entity) or 0.0
                for d in self.solar_devices
            ]
            data["solar_power_total"] = sum(solar_powers)
            data["solar_devices"] = [
                {"name": d.name, "power": p}
                for d, p in zip(self.solar_devices, solar_powers)
            ]

            # Grid: sum all meters (positive = import, negative = export)
            grid_powers = [
                self._get_state_float(d.power_entity) or 0.0
                for d in self.grid_devices
            ]
            data["grid_power_total"] = sum(grid_powers)
            data["grid_devices"] = [
                {"name": d.name, "power": p}
                for d, p in zip(self.grid_devices, grid_powers)
            ]

            # Battery: per unit SOC + power
            data["battery_devices"] = [
                {
                    "name": d.name,
                    "soc": self._get_state_float(d.soc_entity),
                    "power": self._get_state_float(d.power_entity),
                }
                for d in self.battery_devices
            ]
            soc_values = [b["soc"] for b in data["battery_devices"] if b["soc"] is not None]
            data["battery_soc_avg"] = sum(soc_values) / len(soc_values) if soc_values else None
            data["battery_power_total"] = sum(
                b["power"] or 0.0 for b in data["battery_devices"]
            )

            # EV chargers
            data["ev_chargers"] = [
                {
                    "name": ev.name,
                    "power": self._get_state_float(ev.power_entity),
                    "charging": self._get_state_bool(ev.charging_switch),
                }
                for ev in self.ev_chargers
            ]
            data["ev_power_total"] = sum(
                c["power"] or 0.0 for c in data["ev_chargers"]
            )

            # Tariff
            data["current_tariff"] = (
                self._get_state_float(self.tariff.price_entity) if self.tariff else None
            )

            # Heat pumps
            data["heat_pumps"] = [
                {
                    "name": hp.name,
                    "power": self._get_state_float(hp.power_entity),
                }
                for hp in self.heat_pumps
            ]

            # AC units
            data["ac_units"] = [
                {
                    "name": ac.name,
                    "power": self._get_state_float(ac.power_entity),
                }
                for ac in self.ac_units
            ]

            # Pool pumps
            data["pool_pumps"] = [
                {
                    "name": pp.name,
                    "power": self._get_state_float(pp.power_entity),
                }
                for pp in self.pool_pumps
            ]

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
