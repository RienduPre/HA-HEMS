"""Pool pump control logic."""
from __future__ import annotations

import logging
from enum import Enum

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class PoolPumpMode(str, Enum):
    """Pool pump operating modes."""
    OFF = "off"
    NORMAL = "normal"
    SOLAR = "solar"


class PoolPumpController:
    """Controls a single pool pump/heater."""

    def __init__(self, hass: HomeAssistant, pool_pump, coordinator) -> None:
        self.hass = hass
        self.pool_pump = pool_pump
        self.coordinator = coordinator
        self.mode = PoolPumpMode.NORMAL

    async def async_evaluate(self) -> None:
        """Evaluate and control pool pump based on solar availability."""
        data = self.coordinator.data or {}
        grid_w = data.get("grid_power_total") or 0.0
        solar_excess_w = max(0.0, -grid_w)

        if self.mode == PoolPumpMode.OFF:
            await self._set_power(False)

        elif self.mode == PoolPumpMode.NORMAL:
            pass  # Don't control, let user manage

        elif self.mode == PoolPumpMode.SOLAR:
            should_run = solar_excess_w > 500
            if should_run:
                _LOGGER.info(
                    "%s: solar excess %.0f W, enabling",
                    self.pool_pump.name, solar_excess_w,
                )
                await self._set_power(True)
            else:
                _LOGGER.debug(
                    "%s: solar excess %.0f W (need >500W), disabling",
                    self.pool_pump.name, solar_excess_w,
                )
                await self._set_power(False)

    async def _set_power(self, enabled: bool) -> None:
        """Turn pool pump on/off."""
        if not self.pool_pump.switch_entity:
            _LOGGER.warning("%s: no power switch configured", self.pool_pump.name)
            return

        service = "turn_on" if enabled else "turn_off"
        await self.hass.services.async_call(
            "switch",
            service,
            {"entity_id": self.pool_pump.switch_entity},
            blocking=True,
        )
        _LOGGER.debug("%s: power set to %s", self.pool_pump.name, enabled)
