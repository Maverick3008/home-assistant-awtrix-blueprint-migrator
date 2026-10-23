"""Config flow for AWTRIX Blueprint Migrator."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    CONF_NAME_PREFIX,
    CONF_TARGET_AWTRIX_DEVICE,
    DEFAULT_NAME_PREFIX,
    DOMAIN,
)


def _user_schema(default_target: str | None = None, default_prefix: str = DEFAULT_NAME_PREFIX):
    """Return the setup schema with a real Home Assistant device selector."""
    target_key = (
        vol.Required(CONF_TARGET_AWTRIX_DEVICE, default=default_target)
        if default_target
        else vol.Required(CONF_TARGET_AWTRIX_DEVICE)
    )

    return vol.Schema(
        {
            target_key: selector.selector(
                {
                    "device": {
                        "filter": [
                            {
                                "integration": "mqtt",
                                "manufacturer": "Blueforcer",
                            }
                        ],
                        "multiple": False,
                    }
                }
            ),
            vol.Required(CONF_NAME_PREFIX, default=default_prefix): selector.TextSelector(),
        }
    )


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for AWTRIX Blueprint Migrator."""

    VERSION = 2

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle setup initiated by the user."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(
                title="AWTRIX Blueprint Migrator",
                data={
                    CONF_TARGET_AWTRIX_DEVICE: user_input[CONF_TARGET_AWTRIX_DEVICE],
                    CONF_NAME_PREFIX: user_input.get(
                        CONF_NAME_PREFIX, DEFAULT_NAME_PREFIX
                    ),
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(),
        )
