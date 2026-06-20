"""Heat pump control logic with SG Ready support."""
from __future__ import annotations

import logging
from enum import Enum

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class HeatPumpMode(str, Enum):
    """Heat pump operating modes."""
    OFF = "off"
    NORMAL = "normal"
    SOLAR = "solar"


class HeatPumpController:
    """Controls a single heat pump, optionally via SG Ready."""

    def __init__(self, hass: HomeAssistant, heat_pump, coordinator) -> None:
        self.hass = hass
        self.heat_pump = heat_pump
        self.coordinator = coordinator
        self.mode = HeatPumpMode.NORMAL

    async def async_evaluate(self) -> None:
        """Evaluate and control heat pump based on solar availability."""
        data = self.coordinator.data or {}
        solar_power = data.get("solar_power_total") or 0.0
        grid_w = data.get("grid_power_total") or 0.0
        solar_excess_w = max(0.0, -grid_w)

        if self.mode == HeatPumpMode.OFF:
            await self._set_sgready(False)

        elif self.mode == HeatPumpMode.NORMAL:
            await self._set_sgready(False)

        elif self.mode == HeatPumpMode.SOLAR:
            should_enable = solar_excess_w > 500  # Only enable with substantial solar excess
            if should_enable:
                _LOGGER.info(
                    "%s: solar excess %.0f W, enabling SG Ready",
                    self.heat_pump.name, solar_excess_w,
                )
                await self._set_sgready(True)
            else:
                _LOGGER.debug(
                    "%s: solar excess %.0f W (need >500W), disabling SG Ready",
                    self.heat_pump.name, solar_excess_w,
                )
                await self._set_sgready(False)

    async def _set_sgready(self, enabled: bool) -> None:
        """Enable/disable SG Ready mode."""
        if not self.heat_pump.sgready_switch:
            _LOGGER.warning("%s: no SG Ready switch configured", self.heat_pump.name)
            return

        service = "turn_on" if enabled else "turn_off"
        await self.hass.services.async_call(
            "switch" if "switch" in self.heat_pump.sgready_switch else "binary_sensor",
            service,
            {"entity_id": self.heat_pump.sgready_switch},
            blocking=True,
        )
        _LOGGER.debug("%s: SG Ready set to %s", self.heat_pump.name, enabled)
