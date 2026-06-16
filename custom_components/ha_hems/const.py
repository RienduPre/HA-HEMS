"""Constants for HA-HEMS."""

DOMAIN = "ha_hems"
NAME = "HA-HEMS"
VERSION = "0.1.0"

# Discovery device classes
DEVICE_CLASS_SOLAR = "power"       # production entities
DEVICE_CLASS_GRID = "power"        # grid import/export
DEVICE_CLASS_BATTERY = "battery"   # SOC
DEVICE_CLASS_ENERGY = "energy"     # cumulative kWh

# Config entry keys
CONF_SOLAR_ENTITY = "solar_entity"
CONF_GRID_ENTITY = "grid_entity"
CONF_BATTERY_SOC_ENTITY = "battery_soc_entity"
CONF_BATTERY_POWER_ENTITY = "battery_power_entity"
CONF_EV_CHARGERS = "ev_chargers"
CONF_HEAT_PUMP = "heat_pump"
CONF_TARIFF_ENTITY = "tariff_entity"

# Update interval
UPDATE_INTERVAL_SECONDS = 30
