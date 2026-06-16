"""Scheduling logic for HA-HEMS — decides modes based on time + tariff."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .ev_charger import EVChargingMode, CHEAP_TARIFF_THRESHOLD
from .battery import BatteryMode

_LOGGER = logging.getLogger(__name__)


@dataclass
class HEMSSchedule:
    """Current mode decisions for all devices."""
    ev_mode: EVChargingMode = EVChargingMode.SOLAR
    battery_mode: BatteryMode = BatteryMode.NET_ZERO
    reason: str = ""


class HEMSScheduler:
    """Decides operating modes based on tariff, time, and solar availability."""

    def __init__(self, hass: HomeAssistant, coordinator) -> None:
        self.hass = hass
        self.coordinator = coordinator

    def evaluate(self) -> HEMSSchedule:
        """Return the current recommended schedule."""
        data = self.coordinator.data or {}
        tariff = data.get("current_tariff")
        solar_w = data.get("solar_power") or 0.0
        now: datetime = dt_util.now()
        hour = now.hour

        # Negative tariff: grid is paying us to consume → charge battery + charge EV fast
        if tariff is not None and tariff < 0:
            return HEMSSchedule(
                ev_mode=EVChargingMode.FAST,
                battery_mode=BatteryMode.CHARGE,
                reason=f"Negative tariff ({tariff:.4f} €/kWh): maximize consumption",
            )

        # Very cheap tariff (e.g. < 0.05 €/kWh): charge battery + EV
        if tariff is not None and tariff < 0.05:
            return HEMSSchedule(
                ev_mode=EVChargingMode.FAST,
                battery_mode=BatteryMode.CHARGE,
                reason=f"Very cheap tariff ({tariff:.4f} €/kWh): opportunistic charging",
            )

        # Cheap tariff (< threshold): EV solar or cheap
        if tariff is not None and tariff < CHEAP_TARIFF_THRESHOLD:
            return HEMSSchedule(
                ev_mode=EVChargingMode.SOLAR_OR_CHEAP,
                battery_mode=BatteryMode.NET_ZERO,
                reason=f"Cheap tariff ({tariff:.4f} €/kWh): solar or cheap EV charging",
            )

        # Expensive tariff (> 0.30 €/kWh): discharge battery to offset grid import
        if tariff is not None and tariff > 0.30:
            return HEMSSchedule(
                ev_mode=EVChargingMode.SOLAR,
                battery_mode=BatteryMode.DISCHARGE,
                reason=f"Expensive tariff ({tariff:.4f} €/kWh): discharging battery",
            )

        # Default: solar steering for EV, net-zero for battery
        return HEMSSchedule(
            ev_mode=EVChargingMode.SOLAR,
            battery_mode=BatteryMode.NET_ZERO,
            reason="Default: solar steering",
        )
