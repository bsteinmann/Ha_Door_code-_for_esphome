"""Websocket API for the Door Code Manager panel (admin only)."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, SIGNAL_UPDATE

_DATE = vol.Any(None, str)
_FIELDS = {
    vol.Optional("name"): vol.All(str, vol.Length(min=1, max=40)),
    vol.Optional("code"): str,
    vol.Optional("enabled"): bool,
    vol.Optional("one_time"): bool,
    vol.Optional("notify"): bool,
    vol.Optional("valid_from"): _DATE,
    vol.Optional("expires_at"): _DATE,
}


@callback
def async_setup(hass: HomeAssistant) -> None:
    for command in (ws_subscribe, ws_add, ws_update, ws_delete):
        websocket_api.async_register_command(hass, command)


def _manager(hass, connection, msg):
    manager = hass.data.get(DOMAIN)
    if manager is None:
        connection.send_error(msg["id"], "not_loaded", "Door Code Manager ist nicht geladen.")
    return manager


def _payload(msg) -> dict:
    return {k: v for k, v in msg.items() if k not in ("id", "type", "code_id")}


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/subscribe"})
@callback
def ws_subscribe(hass, connection, msg) -> None:
    manager = _manager(hass, connection, msg)
    if manager is None:
        return

    @callback
    def forward() -> None:
        connection.send_message(websocket_api.event_message(msg["id"], manager.snapshot()))

    connection.subscriptions[msg["id"]] = async_dispatcher_connect(hass, SIGNAL_UPDATE, forward)
    connection.send_result(msg["id"])
    forward()


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/add",
        vol.Required("name"): vol.All(str, vol.Length(min=1, max=40)),
        vol.Required("code"): str,
        **{k: v for k, v in _FIELDS.items() if k.schema not in ("name", "code")},
    }
)
@websocket_api.async_response
async def ws_add(hass, connection, msg) -> None:
    manager = _manager(hass, connection, msg)
    if manager is None:
        return
    try:
        result = await manager.async_add(_payload(msg))
    except HomeAssistantError as err:
        connection.send_error(msg["id"], "failed", str(err))
        return
    connection.send_result(msg["id"], {"id": result["id"]})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/update", vol.Required("code_id"): str, **_FIELDS}
)
@websocket_api.async_response
async def ws_update(hass, connection, msg) -> None:
    manager = _manager(hass, connection, msg)
    if manager is None:
        return
    try:
        await manager.async_update(msg["code_id"], _payload(msg))
    except HomeAssistantError as err:
        connection.send_error(msg["id"], "failed", str(err))
        return
    connection.send_result(msg["id"])


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/delete", vol.Required("code_id"): str}
)
@websocket_api.async_response
async def ws_delete(hass, connection, msg) -> None:
    manager = _manager(hass, connection, msg)
    if manager is None:
        return
    try:
        await manager.async_delete(msg["code_id"])
    except HomeAssistantError as err:
        connection.send_error(msg["id"], "failed", str(err))
        return
    connection.send_result(msg["id"])
