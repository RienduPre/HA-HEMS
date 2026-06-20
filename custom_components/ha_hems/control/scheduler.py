"""Scheduling logic for HA-HEMS — reads tunable thresholds from options."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from ..const import (
    CONF_CHEAP_TARIFF_THRESHOLD,
    CONF_EXPENSIVE_TARIFF_THRESHOLD,
    DEFAULT_CHEAP_TARIFF_THRESHOLD,
    DEFAULT_EXPENSIVE_TARIFF_THRESHOLD,
)
from .ev_charger import EVChargingMode
from .battery import BatteryMode
from .heat_pump import HeatPumpMode
from .ac import ACMode
from .pool_pump import PoolPumpMode

_LOGGER = logging.getLogger(__name__)


@dataclass
class HEMSSchedule:
    """Current mode decisions for all devices."""
    ev_mode: EVChargingMode = EVChargingMode.SOLAR
    battery_mode: BatteryMode = BatteryMode.NET_ZERO
    heat_pump_mode: HeatPumpMode = HeatPumpMode.NORMAL
    ac_mode: ACMode = ACMode.NORMAL
    pool_pump_mode: PoolPumpMode = PoolPumpMode.NORMAL
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

        options = self.coordinator.entry.options
        cheap = options.get(CONF_CHEAP_TARIFF_THRESHOLD, DEFAULT_CHEAP_TARIFF_THRESHOLD)
        expensive = options.get(CONF_EXPENSIVE_TARIFF_THRESHOLD, DEFAULT_EXPENSIVE_TARIFF_THRESHOLD)

        if tariff is not None and tariff < 0:
            return HEMSSchedule(
                ev_mode=EVChargingMode.FAST,
                battery_mode=BatteryMode.CHARGE,
                heat_pump_mode=HeatPumpMode.SOLAR,
                ac_mode=ACMode.SOLAR,
                pool_pump_mode=PoolPumpMode.SOLAR,
                reason=f"Negative tariff ({tariff:.4f} €/kWh): maximize consumption",
            )

        if tariff is not None and tariff < cheap / 2:
            return HEMSSchedule(
                ev_mode=EVChargingMode.FAST,
                battery_mode=BatteryMode.CHARGE,
                heat_pump_mode=HeatPumpMode.SOLAR,
                ac_mode=ACMode.SOLAR,
                pool_pump_mode=PoolPumpMode.SOLAR,
                reason=f"Very cheap tariff ({tariff:.4f} €/kWh): opportunistic charging",
            )

        if tariff is not None and tariff < cheap:
            return HEMSSchedule(
                ev_mode=EVChargingMode.SOLAR_OR_CHEAP,
                battery_mode=BatteryMode.NET_ZERO,
                heat_pump_mode=HeatPumpMode.SOLAR,
                ac_mode=ACMode.SOLAR,
                pool_pump_mode=PoolPumpMode.SOLAR,
                reason=f"Cheap tariff ({tariff:.4f} €/kWh): solar or cheap EV charging",
            )

        if tariff is not None and tariff > expensive:
            return HEMSSchedule(
                ev_mode=EVChargingMode.SOLAR,
                battery_mode=BatteryMode.DISCHARGE,
                heat_pump_mode=HeatPumpMode.NORMAL,
                ac_mode=ACMode.NORMAL,
                pool_pump_mode=PoolPumpMode.NORMAL,
                reason=f"Expensive tariff ({tariff:.4f} €/kWh): discharging battery",
            )

        return HEMSSchedule(
            ev_mode=EVChargingMode.SOLAR,
            battery_mode=BatteryMode.NET_ZERO,
            heat_pump_mode=HeatPumpMode.NORMAL,
            ac_mode=ACMode.NORMAL,
            pool_pump_mode=PoolPumpMode.NORMAL,
            reason="Default: solar steering",
        )
