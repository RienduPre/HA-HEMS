"""Home battery control logic for HA-HEMS."""
from __future__ import annotations

import logging
from enum import Enum

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class BatteryMode(str, Enum):
    """Battery control modes."""
    OFF = "off"             # Do nothing, let inverter decide
    NET_ZERO = "net_zero"   # Minimize grid import/export
    CHARGE = "charge"       # Force charge (e.g. cheap tariff)
    DISCHARGE = "discharge" # Force discharge (e.g. expensive tariff)


# Thresholds
GRID_DEADBAND_W = 50        # Ignore grid imbalance below this (W)
MAX_CHARGE_POWER_W = 3000   # Default max charge rate (W)
MAX_DISCHARGE_POWER_W = 3000
SOC_MIN_PCT = 10            # Never discharge below this
SOC_MAX_PCT = 95            # Never charge above this


class BatteryController:
    """Controls the home battery."""

    def __init__(self, hass: HomeAssistant, battery, coordinator) -> None:
        self.hass = hass
        self.battery = battery
        self.coordinator = coordinator
        self.mode = BatteryMode.NET_ZERO

    async def async_evaluate(self) -> None:
        """Evaluate and send setpoint to battery."""
        data = self.coordinator.data or {}
        grid_w = data.get("grid_power_total") or 0.0
        soc_values = [b["soc"] for b in data.get("battery_devices", []) if b.get("soc") is not None]
        soc = soc_values[0] if soc_values else None

        if soc is None:
            _LOGGER.warning("Battery: SOC unknown, skipping control")
            return

        if self.mode == BatteryMode.OFF:
            return

        elif self.mode == BatteryMode.NET_ZERO:
            await self._control_net_zero(grid_w, soc)

        elif self.mode == BatteryMode.CHARGE:
            if soc < SOC_MAX_PCT:
                await self._set_power(-MAX_CHARGE_POWER_W)  # negative = charge
            else:
                _LOGGER.info("Battery: SOC %.0f%% at max, skipping charge", soc)

        elif self.mode == BatteryMode.DISCHARGE:
            if soc > SOC_MIN_PCT:
                await self._set_power(MAX_DISCHARGE_POWER_W)
            else:
                _LOGGER.info("Battery: SOC %.0f%% at min, skipping discharge", soc)

    async def _control_net_zero(self, grid_w: float, soc: float) -> None:
        """Drive grid import/export toward zero."""
        if abs(grid_w) < GRID_DEADBAND_W:
            return  # Within deadband, no action needed

        # grid_w > 0 = importing → discharge battery
        # grid_w < 0 = exporting → charge battery
        setpoint_w = -grid_w  # Invert: offset what the grid is doing

        # Clamp to SOC limits
        if setpoint_w > 0 and soc <= SOC_MIN_PCT:
            _LOGGER.debug("Battery net-zero: would discharge but SOC at minimum")
            return
        if setpoint_w < 0 and soc >= SOC_MAX_PCT:
            _LOGGER.debug("Battery net-zero: would charge but SOC at maximum")
            return

        # Clamp to max power
        setpoint_w = max(-MAX_CHARGE_POWER_W, min(MAX_DISCHARGE_POWER_W, setpoint_w))

        await self._set_power(setpoint_w)

    async def _set_power(self, watts: float) -> None:
        """Send power setpoint to battery via number entity."""
        if not self.battery.power_entity:
            _LOGGER.warning("Battery: no power setpoint entity configured")
            return

        await self.hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": self.battery.power_entity, "value": watts},
            blocking=True,
        )
        _LOGGER.debug("Battery: setpoint set to %.0f W", watts)
