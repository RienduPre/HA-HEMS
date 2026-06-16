"""EV charger control logic for HA-HEMS."""
from __future__ import annotations

import logging
from enum import Enum

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class EVChargingMode(str, Enum):
    """Charging modes for the EV charger."""
    OFF = "off"                     # Do not charge
    SOLAR = "solar"                 # Charge on solar excess only
    SOLAR_OR_CHEAP = "solar_or_cheap"  # Solar excess OR cheap tariff
    FAST = "fast"                   # Charge as fast as possible


# Thresholds
SOLAR_EXCESS_THRESHOLD_W = 300     # Minimum solar excess to start charging (W)
SOLAR_STOP_THRESHOLD_W = 100       # Stop charging below this solar excess (W)
CHEAP_TARIFF_THRESHOLD = 0.10      # €/kWh — below this is "cheap"
MIN_CHARGE_POWER_W = 1380          # ~6A single phase minimum


class EVChargerController:
    """Controls a single EV charger."""

    def __init__(self, hass: HomeAssistant, charger, coordinator) -> None:
        """Initialize."""
        self.hass = hass
        self.charger = charger
        self.coordinator = coordinator
        self.mode = EVChargingMode.SOLAR

    async def async_evaluate(self) -> None:
        """Evaluate current state and act."""
        data = self.coordinator.data or {}
        solar_w = data.get("solar_power") or 0.0
        grid_w = data.get("grid_power") or 0.0  # positive = import
        tariff = data.get("current_tariff")

        # Solar excess = what we're pushing back to grid (negative grid = export)
        solar_excess_w = max(0.0, -grid_w)

        currently_charging = self.coordinator._get_state_bool(self.charger.charging_switch)

        if self.mode == EVChargingMode.OFF:
            if currently_charging:
                await self._set_charging(False)

        elif self.mode == EVChargingMode.FAST:
            if not currently_charging:
                await self._set_charging(True)

        elif self.mode == EVChargingMode.SOLAR:
            await self._control_solar(solar_excess_w, currently_charging)

        elif self.mode == EVChargingMode.SOLAR_OR_CHEAP:
            cheap = tariff is not None and tariff < CHEAP_TARIFF_THRESHOLD
            if cheap:
                if not currently_charging:
                    _LOGGER.info("%s: cheap tariff (%.4f €/kWh), starting charge", self.charger.name, tariff)
                    await self._set_charging(True)
            else:
                await self._control_solar(solar_excess_w, currently_charging)

    async def _control_solar(self, solar_excess_w: float, currently_charging: bool) -> None:
        """Start/stop charging based on solar excess."""
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
        """Enable or disable charging via the switch entity."""
        service = "turn_on" if enabled else "turn_off"
        await self.hass.services.async_call(
            "switch",
            service,
            {"entity_id": self.charger.charging_switch},
            blocking=True,
        )
        _LOGGER.debug("%s: charging set to %s", self.charger.name, enabled)
