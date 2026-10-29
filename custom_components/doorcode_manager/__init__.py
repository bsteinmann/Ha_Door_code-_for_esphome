"""Door Code Manager – manage keypad codes with a sidebar UI."""
from __future__ import annotations

from pathlib import Path

import voluptuous as vol

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from . import api
from .const import DOMAIN, PANEL_PATH, PANEL_URL, VERSION
from .manager import DoorCodeManager

PLATFORMS = [Platform.SENSOR]
_STATIC_KEY = f"{DOMAIN}_static_registered"

_DATE = vol.Any(None, cv.string)
ADD_SCHEMA = vol.Schema(
    {
        vol.Required("name"): cv.string,
        vol.Optional("code"): vol.Any(None, cv.string),
        vol.Optional("kind", default="person"): vol.In(["person", "action"]),
        vol.Optional("tags"): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional("open_door", default=True): cv.boolean,
        vol.Optional("actions"): vol.All(cv.ensure_list, [cv.entity_id]),
        vol.Optional("enabled", default=True): cv.boolean,
        vol.Optional("one_time", default=False): cv.boolean,
        vol.Optional("notify", default=True): cv.boolean,
        vol.Optional("valid_from"): _DATE,
        vol.Optional("expires_at"): _DATE,
    }
)
ID_SCHEMA = vol.Schema({vol.Required("code_id"): cv.string})


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    api.async_setup(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    manager = DoorCodeManager(hass, entry)
    await manager.async_start()
    hass.data[DOMAIN] = manager

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _register_services(hass, manager)
    await _register_panel(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    await hass.data.pop(DOMAIN).async_stop()
    for service in ("add_code", "delete_code", "enable_code", "disable_code"):
        hass.services.async_remove(DOMAIN, service)
    frontend.async_remove_panel(hass, PANEL_PATH, warn_if_unknown=False)
    return True


def _register_services(hass: HomeAssistant, manager: DoorCodeManager) -> None:
    async def add_code(call: ServiceCall) -> None:
        await manager.async_add(dict(call.data))

    async def delete_code(call: ServiceCall) -> None:
        await manager.async_delete(call.data["code_id"])

    async def enable_code(call: ServiceCall) -> None:
        await manager.async_update(call.data["code_id"], {"enabled": True})

    async def disable_code(call: ServiceCall) -> None:
        await manager.async_update(call.data["code_id"], {"enabled": False})

    hass.services.async_register(DOMAIN, "add_code", add_code, schema=ADD_SCHEMA)
    hass.services.async_register(DOMAIN, "delete_code", delete_code, schema=ID_SCHEMA)
    hass.services.async_register(DOMAIN, "enable_code", enable_code, schema=ID_SCHEMA)
    hass.services.async_register(DOMAIN, "disable_code", disable_code, schema=ID_SCHEMA)


async def _register_panel(hass: HomeAssistant) -> None:
    if not hass.data.get(_STATIC_KEY):
        js = Path(__file__).parent / "frontend" / "doorcode-panel.js"
        await hass.http.async_register_static_paths(
            [StaticPathConfig(PANEL_URL, str(js), cache_headers=False)]
        )
        hass.data[_STATIC_KEY] = True
    await panel_custom.async_register_panel(
        hass,
        webcomponent_name="doorcode-panel",
        frontend_url_path=PANEL_PATH,
        module_url=f"{PANEL_URL}?v={VERSION}",
        sidebar_title="Türcodes",
        sidebar_icon="mdi:dialpad",
        require_admin=True,
        config={},
        embed_iframe=False,
    )
