"""HA-HEMS: Home Assistant Home Energy Management System."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import HEMSCoordinator
from .control.manager import HEMSManager

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HA-HEMS from a config entry."""
    coordinator = HEMSCoordinator(hass, entry)

    # Run device discovery
    await coordinator.async_discover_devices()

    # Set up control manager and wire it to the coordinator
    manager = HEMSManager(hass, coordinator)
    await manager.async_setup()
    coordinator.set_manager(manager)

    # First data refresh (also triggers first control evaluation)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
