"""Config flow for HA-HEMS."""
from __future__ import annotations

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
)


class HEMSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial setup flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Step 1: optional manual entity overrides."""
        if user_input is not None:
            # Strip empty strings
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
            description_placeholders={
                "info": "Laat velden leeg voor automatische discovery."
            },
        )
