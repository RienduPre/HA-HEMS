"""Config flow for HA-HEMS."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_SOLAR_ENTITY,
    CONF_GRID_ENTITY,
    CONF_BATTERY_SOC_ENTITY,
    CONF_BATTERY_POWER_ENTITY,
    CONF_TARIFF_ENTITY,
    CONF_SOLAR_EXCESS_THRESHOLD,
    CONF_SOLAR_STOP_THRESHOLD,
    CONF_CHEAP_TARIFF_THRESHOLD,
    CONF_EXPENSIVE_TARIFF_THRESHOLD,
    DEFAULT_SOLAR_EXCESS_THRESHOLD,
    DEFAULT_SOLAR_STOP_THRESHOLD,
    DEFAULT_CHEAP_TARIFF_THRESHOLD,
    DEFAULT_EXPENSIVE_TARIFF_THRESHOLD,
)

_LOGGER = logging.getLogger(__name__)


class HEMSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial setup flow.

    HA-HEMS works fully automatic via discovery. This step only offers
    optional manual overrides for edge cases where auto-discovery fails
    or picks the wrong entity. Multiple devices are supported — manual
    overrides here only apply to single-device fallback fields; for
    multi-device setups, leave these empty and use discovery, or edit
    options afterwards.
    """

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Step 1: optional manual entity overrides + confirm."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Prevent duplicate config entries
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            data = {k: v for k, v in user_input.items() if v}
            return self.async_create_entry(title="HA-HEMS", data=data)

        schema = vol.Schema(
            {
                vol.Optional(CONF_SOLAR_ENTITY, default=""): str,
                vol.Optional(CONF_GRID_ENTITY, default=""): str,
                vol.Optional(CONF_BATTERY_SOC_ENTITY, default=""): str,
                vol.Optional(CONF_BATTERY_POWER_ENTITY, default=""): str,
                vol.Optional(CONF_TARIFF_ENTITY, default=""): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> HEMSOptionsFlow:
        """Get the options flow for this handler."""
        return HEMSOptionsFlow(config_entry)


class HEMSOptionsFlow(config_entries.OptionsFlow):
    """Handle options — tune thresholds without reinstalling."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage the thresholds."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SOLAR_EXCESS_THRESHOLD,
                    default=options.get(CONF_SOLAR_EXCESS_THRESHOLD, DEFAULT_SOLAR_EXCESS_THRESHOLD),
                ): vol.Coerce(int),
                vol.Optional(
                    CONF_SOLAR_STOP_THRESHOLD,
                    default=options.get(CONF_SOLAR_STOP_THRESHOLD, DEFAULT_SOLAR_STOP_THRESHOLD),
                ): vol.Coerce(int),
                vol.Optional(
                    CONF_CHEAP_TARIFF_THRESHOLD,
                    default=options.get(CONF_CHEAP_TARIFF_THRESHOLD, DEFAULT_CHEAP_TARIFF_THRESHOLD),
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_EXPENSIVE_TARIFF_THRESHOLD,
                    default=options.get(CONF_EXPENSIVE_TARIFF_THRESHOLD, DEFAULT_EXPENSIVE_TARIFF_THRESHOLD),
                ): vol.Coerce(float),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
