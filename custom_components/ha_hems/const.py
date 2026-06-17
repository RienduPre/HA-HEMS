"""Constants for HA-HEMS."""

DOMAIN = "ha_hems"
NAME = "HA-HEMS"
VERSION = "0.1.0"

# Discovery device classes
DEVICE_CLASS_SOLAR = "power"
DEVICE_CLASS_GRID = "power"
DEVICE_CLASS_BATTERY = "battery"
DEVICE_CLASS_ENERGY = "energy"

# Config entry keys (manual single-device override / initial setup)
CONF_SOLAR_ENTITY = "solar_entity"
CONF_GRID_ENTITY = "grid_entity"
CONF_BATTERY_SOC_ENTITY = "battery_soc_entity"
CONF_BATTERY_POWER_ENTITY = "battery_power_entity"
CONF_EV_CHARGERS = "ev_chargers"
CONF_HEAT_PUMP = "heat_pump"
CONF_TARIFF_ENTITY = "tariff_entity"

# Options flow keys (tunable thresholds)
CONF_SOLAR_EXCESS_THRESHOLD = "solar_excess_threshold"
CONF_SOLAR_STOP_THRESHOLD = "solar_stop_threshold"
CONF_CHEAP_TARIFF_THRESHOLD = "cheap_tariff_threshold"
CONF_EXPENSIVE_TARIFF_THRESHOLD = "expensive_tariff_threshold"

DEFAULT_SOLAR_EXCESS_THRESHOLD = 300    # W — start EV charging above this
DEFAULT_SOLAR_STOP_THRESHOLD = 100      # W — stop EV charging below this
DEFAULT_CHEAP_TARIFF_THRESHOLD = 0.10   # €/kWh
DEFAULT_EXPENSIVE_TARIFF_THRESHOLD = 0.30  # €/kWh

# Update interval
UPDATE_INTERVAL_SECONDS = 30
