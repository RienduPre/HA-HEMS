"""Select platform for HA-HEMS — manual EV charging mode override per charger."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HEMSCoordinator
from .control.ev_charger import EVChargingMode

_LOGGER = logging.getLogger(__name__)

EV_MODE_OPTIONS = [m.value for m in EVChargingMode]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up mode-select entities for each EV charger and an overall HEMS mode."""
    coordinator: HEMSCoordinator = hass.data[DOMAIN][entry.entry_id]
    manager = coordinator._manager

    entities = []

    # One select per EV charger — "auto" (follow scheduler) or a forced mode
    for i, controller in enumerate(manager.ev_controllers):
        entities.append(HEMSEVModeSelect(coordinator, controller, i))

    # One overall select — lets you force the whole house into a mode
    entities.append(HEMSGlobalModeSelect(coordinator, manager))

    async_add_entities(entities)


class HEMSEVModeSelect(CoordinatorEntity, SelectEntity):
    """Lets the user override the charging mode for one EV charger.

    Selecting 'auto' hands control back to the scheduler.
    """

    _attr_options = ["auto"] + EV_MODE_OPTIONS

    def __init__(self, coordinator, controller, index: int) -> None:
        super().__init__(coordinator)
        self._controller = controller
        self._attr_unique_id = f"ha_hems_ev_{index}_mode_select"
        self._attr_name = f"HEMS EV {controller.charger.name} Mode"
        self._attr_icon = "mdi:ev-station"
        self._current = "auto"

    @property
    def current_option(self) -> str:
        return self._current

    async def async_select_option(self, option: str) -> None:
        """Change the selected mode."""
        self._current = option
        if option == "auto":
            self._controller.manual_override = None
            _LOGGER.info("%s: mode set to auto (scheduler controls)", self._controller.charger.name)
        else:
            self._controller.manual_override = EVChargingMode(option)
            _LOGGER.info("%s: mode manually set to %s", self._controller.charger.name, option)
        self.async_write_ha_state()


class HEMSGlobalModeSelect(CoordinatorEntity, SelectEntity):
    """Lets the user force ALL EV chargers into the same mode at once."""

    _attr_options = ["auto"] + EV_MODE_OPTIONS

    def __init__(self, coordinator, manager) -> None:
        super().__init__(coordinator)
        self._manager = manager
        self._attr_unique_id = "ha_hems_global_mode_select"
        self._attr_name = "HEMS Mode (All Chargers)"
        self._attr_icon = "mdi:home-lightning-bolt"
        self._current = "auto"

    @property
    def current_option(self) -> str:
        return self._current

    async def async_select_option(self, option: str) -> None:
        self._current = option
        override = None if option == "auto" else EVChargingMode(option)
        for controller in self._manager.ev_controllers:
            controller.manual_override = override
        _LOGGER.info("Global EV mode set to %s for all %d charger(s)", option, len(self._manager.ev_controllers))
        self.async_write_ha_state()
