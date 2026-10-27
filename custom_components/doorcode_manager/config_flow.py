"""Config flow for Door Code Manager."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_DOOR,
    CONF_KEYPAD,
    CONF_NOTIFY,
    CONF_TRIGGER,
    DEFAULT_LOCKOUT,
    DEFAULT_MAX_FAILED,
    DEFAULT_PULSE,
    DOMAIN,
    OPT_LOCKOUT,
    OPT_MAX_FAILED,
    OPT_NOTIFY_DEFAULT,
    OPT_PULSE,
    OPT_TAG_DEVICES,
)


class DoorCodeManagerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the setup dialog."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(title="Door Code Manager", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_KEYPAD): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_TRIGGER): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="binary_sensor")
                ),
                vol.Required(CONF_DOOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["switch", "button", "lock"])
                ),
                vol.Optional(CONF_NOTIFY): selector.TextSelector(),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return DoorCodeManagerOptionsFlow()


class DoorCodeManagerOptionsFlow(config_entries.OptionsFlow):
    """Handle options."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        o = self.config_entry.options
        manager = self.hass.data.get(DOMAIN)
        choices = [
            selector.SelectOptionDict(value=t["service"], label=t["label"])
            for t in (manager.notify_targets() if manager else [])
        ]
        schema = vol.Schema(
            {
                vol.Required(OPT_PULSE, default=o.get(OPT_PULSE, DEFAULT_PULSE)): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=60)
                ),
                vol.Required(
                    OPT_MAX_FAILED, default=o.get(OPT_MAX_FAILED, DEFAULT_MAX_FAILED)
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=20)),
                vol.Required(OPT_LOCKOUT, default=o.get(OPT_LOCKOUT, DEFAULT_LOCKOUT)): vol.All(
                    vol.Coerce(int), vol.Range(min=10, max=3600)
                ),
                vol.Optional(
                    OPT_TAG_DEVICES, default=o.get(OPT_TAG_DEVICES, [])
                ): selector.DeviceSelector(selector.DeviceSelectorConfig(multiple=True)),
                vol.Optional(
                    OPT_NOTIFY_DEFAULT, default=o.get(OPT_NOTIFY_DEFAULT, [])
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=choices,
                        multiple=True,
                        custom_value=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
