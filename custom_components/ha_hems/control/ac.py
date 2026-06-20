"""Air conditioning control logic."""
from __future__ import annotations

import logging
from enum import Enum

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class ACMode(str, Enum):
    """AC operating modes."""
    OFF = "off"
    NORMAL = "normal"
    SOLAR = "solar"


class ACController:
    """Controls a single AC unit."""

    def __init__(self, hass: HomeAssistant, ac_unit, coordinator) -> None:
        self.hass = hass
        self.ac_unit = ac_unit
        self.coordinator = coordinator
        self.mode = ACMode.NORMAL

    async def async_evaluate(self) -> None:
        """Evaluate and control AC based on solar availability."""
        data = self.coordinator.data or {}
        grid_w = data.get("grid_power_total") or 0.0
        solar_excess_w = max(0.0, -grid_w)

        if self.mode == ACMode.OFF:
            await self._set_power(False)

        elif self.mode == ACMode.NORMAL:
            pass  # Don't control, let user manage

        elif self.mode == ACMode.SOLAR:
            should_run = solar_excess_w > 500
            if should_run:
                _LOGGER.info(
                    "%s: solar excess %.0f W, enabling",
                    self.ac_unit.name, solar_excess_w,
                )
                await self._set_power(True)
            else:
                _LOGGER.debug(
                    "%s: solar excess %.0f W (need >500W), disabling",
                    self.ac_unit.name, solar_excess_w,
                )
                await self._set_power(False)

    async def _set_power(self, enabled: bool) -> None:
        """Turn AC on/off."""
        if not self.ac_unit.switch_entity:
            _LOGGER.warning("%s: no power switch configured", self.ac_unit.name)
            return

        service = "turn_on" if enabled else "turn_off"
        await self.hass.services.async_call(
            "switch",
            service,
            {"entity_id": self.ac_unit.switch_entity},
            blocking=True,
        )
        _LOGGER.debug("%s: power set to %s", self.ac_unit.name, enabled)
