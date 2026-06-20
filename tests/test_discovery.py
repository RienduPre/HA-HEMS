"""Tests for HA-HEMS discovery modules."""
import pytest
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er

from custom_components.ha_hems.discovery.solar import discover_solar
from custom_components.ha_hems.discovery.grid import discover_grid
from custom_components.ha_hems.discovery.battery import discover_battery
from custom_components.ha_hems.discovery.ev_charger import discover_ev_chargers


@pytest.fixture
def entry(hass):
    """Mock config entry."""
    entry = ConfigEntry(
        version=1,
        domain="ha_hems",
        title="HA-HEMS",
        data={},
        options={},
        entry_id="test",
    )
    return entry


async def test_discover_solar_empty(hass: HomeAssistant, entry: ConfigEntry):
    """Test solar discovery with no entities."""
    devices = await discover_solar(hass, entry)
    assert devices == []


async def test_discover_solar_with_manual_override(hass: HomeAssistant):
    """Test solar discovery with manual override."""
    entry = ConfigEntry(
        version=1,
        domain="ha_hems",
        title="HA-HEMS",
        data={"solar_entities": ["sensor.solar_power"]},
        options={},
        entry_id="test",
    )
    devices = await discover_solar(hass, entry)
    assert len(devices) == 1
    assert devices[0].power_entity == "sensor.solar_power"


async def test_discover_grid_empty(hass: HomeAssistant, entry: ConfigEntry):
    """Test grid discovery with no entities."""
    devices = await discover_grid(hass, entry)
    assert devices == []


async def test_discover_battery_empty(hass: HomeAssistant, entry: ConfigEntry):
    """Test battery discovery with no entities."""
    devices = await discover_battery(hass, entry)
    assert devices == []


async def test_discover_ev_chargers_empty(hass: HomeAssistant, entry: ConfigEntry):
    """Test EV charger discovery with no entities."""
    devices = await discover_ev_chargers(hass, entry)
    assert devices == []
