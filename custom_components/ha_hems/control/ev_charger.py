"""EV charger control logic for HA-HEMS — supports manual override."""
from __future__ import annotations

import logging
from enum import Enum

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class EVChargingMode(str, Enum):
    """Charging modes for the EV charger."""
    OFF = "off"
    SOLAR = "solar"
    SOLAR_OR_CHEAP = "solar_or_cheap"
    FAST = "fast"


SOLAR_EXCESS_THRESHOLD_W = 300
SOLAR_STOP_THRESHOLD_W = 100
CHEAP_TARIFF_THRESHOLD = 0.10
MIN_CHARGE_POWER_W = 1380


class EVChargerController:
    """Controls a single EV charger.

    `mode` is set by the scheduler every cycle. `manual_override`, if set
    by the user via the select entity, takes priority over the scheduler.
    """

    def __init__(self, hass: HomeAssistant, charger, coordinator) -> None:
        self.hass = hass
        self.charger = charger
        self.coordinator = coordinator
        self.mode = EVChargingMode.SOLAR        # set by scheduler each cycle
        self.manual_override: EVChargingMode | None = None  # set by user

    @property
    def effective_mode(self) -> EVChargingMode:
        """The mode actually used: manual override wins over scheduler."""
        return self.manual_override if self.manual_override is not None else self.mode

    async def async_evaluate(self) -> None:
        """Evaluate current state and act, using the effective mode."""
        data = self.coordinator.data or {}
        grid_w = data.get("grid_power_total") or 0.0
        tariff = data.get("current_tariff")

        solar_excess_w = max(0.0, -grid_w)
        currently_charging = self.coordinator._get_state_bool(self.charger.charging_switch)

        mode = self.effective_mode

        if mode == EVChargingMode.OFF:
            if currently_charging:
                await self._set_charging(False)

        elif mode == EVChargingMode.FAST:
            if not currently_charging:
                await self._set_charging(True)

        elif mode == EVChargingMode.SOLAR:
            await self._control_solar(solar_excess_w, currently_charging)

        elif mode == EVChargingMode.SOLAR_OR_CHEAP:
            cheap = tariff is not None and tariff < CHEAP_TARIFF_THRESHOLD
            if cheap:
                if not currently_charging:
                    _LOGGER.info("%s: cheap tariff (%.4f €/kWh), starting charge", self.charger.name, tariff)
                    await self._set_charging(True)
            else:
                await self._control_solar(solar_excess_w, currently_charging)

    async def _control_solar(self, solar_excess_w: float, currently_charging: bool) -> None:
        if not currently_charging and solar_excess_w >= SOLAR_EXCESS_THRESHOLD_W:
            _LOGGER.info(
                "%s: solar excess %.0f W >= threshold %d W, starting charge",
                self.charger.name, solar_excess_w, SOLAR_EXCESS_THRESHOLD_W,
            )
            await self._set_charging(True)
        elif currently_charging and solar_excess_w < SOLAR_STOP_THRESHOLD_W:
            _LOGGER.info(
                "%s: solar excess %.0f W < stop threshold %d W, stopping charge",
                self.charger.name, solar_excess_w, SOLAR_STOP_THRESHOLD_W,
            )
            await self._set_charging(False)

    async def _set_charging(self, enabled: bool) -> None:
        service = "turn_on" if enabled else "turn_off"
        await self.hass.services.async_call(
            "switch", service, {"entity_id": self.charger.charging_switch}, blocking=True,
        )
        _LOGGER.debug("%s: charging set to %s", self.charger.name, enabled)
