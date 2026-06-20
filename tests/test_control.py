"""Tests for HA-HEMS scheduler and control logic."""
import pytest
from unittest.mock import MagicMock, AsyncMock
from homeassistant.config_entries import ConfigEntry

from custom_components.ha_hems.control.scheduler import HEMSScheduler, HEMSSchedule
from custom_components.ha_hems.control.ev_charger import EVChargingMode, EVChargerController
from custom_components.ha_hems.control.battery import BatteryMode, BatteryController


@pytest.fixture
def coordinator():
    """Mock coordinator."""
    coord = MagicMock()
    coord.entry = MagicMock()
    coord.entry.options = {}
    coord.data = {
        "solar_power_total": 5000,
        "grid_power_total": 0,
        "battery_devices": [{"soc": 50, "power": 0}],
        "ev_chargers": [],
        "current_tariff": 0.15,
    }
    return coord


def test_scheduler_default_mode(coordinator):
    """Test scheduler returns solar steering by default."""
    scheduler = HEMSScheduler(MagicMock(), coordinator)
    schedule = scheduler.evaluate()
    assert schedule.ev_mode == EVChargingMode.SOLAR
    assert schedule.battery_mode == BatteryMode.NET_ZERO
    assert "solar steering" in schedule.reason.lower()


def test_scheduler_negative_tariff(coordinator):
    """Test scheduler with negative tariff."""
    coordinator.data["current_tariff"] = -0.05
    scheduler = HEMSScheduler(MagicMock(), coordinator)
    schedule = scheduler.evaluate()
    assert schedule.ev_mode == EVChargingMode.FAST
    assert schedule.battery_mode == BatteryMode.CHARGE


def test_scheduler_cheap_tariff(coordinator):
    """Test scheduler with cheap tariff."""
    coordinator.data["current_tariff"] = 0.08
    coordinator.entry.options = {"cheap_tariff_threshold": 0.10}
    scheduler = HEMSScheduler(MagicMock(), coordinator)
    schedule = scheduler.evaluate()
    assert schedule.ev_mode == EVChargingMode.SOLAR_OR_CHEAP
    assert schedule.battery_mode == BatteryMode.NET_ZERO


def test_scheduler_expensive_tariff(coordinator):
    """Test scheduler with expensive tariff."""
    coordinator.data["current_tariff"] = 0.40
    coordinator.entry.options = {"expensive_tariff_threshold": 0.30}
    scheduler = HEMSScheduler(MagicMock(), coordinator)
    schedule = scheduler.evaluate()
    assert schedule.ev_mode == EVChargingMode.SOLAR
    assert schedule.battery_mode == BatteryMode.DISCHARGE


@pytest.mark.asyncio
async def test_ev_charger_solar_excess(coordinator):
    """Test EV charger starts charging on solar excess."""
    hass = MagicMock()
    coordinator._get_state_bool = MagicMock(return_value=False)
    coordinator.data["grid_power_total"] = -500  # Solar excess
    coordinator.data["battery_devices"] = [{"soc": 50}]

    charger = MagicMock()
    charger.name = "Test Charger"
    charger.power_entity = "sensor.charger_power"
    charger.charging_switch = "switch.charger"

    ctrl = EVChargerController(hass, charger, coordinator)
    ctrl.mode = EVChargingMode.SOLAR

    await ctrl.async_evaluate()

    hass.services.async_call.assert_called_once()


@pytest.mark.asyncio
async def test_ev_charger_battery_protection(coordinator):
    """Test EV charger doesn't charge when battery is too low."""
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    coordinator._get_state_bool = MagicMock(return_value=False)
    coordinator.data["grid_power_total"] = -500  # Solar excess
    coordinator.data["battery_devices"] = [{"soc": 15}]  # Low battery

    charger = MagicMock()
    charger.name = "Test Charger"
    charger.power_entity = "sensor.charger_power"
    charger.charging_switch = "switch.charger"

    ctrl = EVChargerController(hass, charger, coordinator)
    ctrl.mode = EVChargingMode.SOLAR

    await ctrl.async_evaluate()

    # Should not call turn_on because battery is too low
    hass.services.async_call.assert_not_called()
