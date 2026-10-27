"""Core logic of Door Code Manager."""
from __future__ import annotations

import logging
import uuid
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CONF_DOOR,
    CONF_KEYPAD,
    CONF_NOTIFY,
    CONF_TRIGGER,
    DEFAULT_LOCKOUT,
    DEFAULT_MAX_FAILED,
    DEFAULT_PULSE,
    DOMAIN,
    EDITABLE,
    EVENT_CODE_ADDED,
    EVENT_CODE_DELETED,
    EVENT_CODE_USED,
    EVENT_INVALID_CODE,
    EVENT_LOCKOUT,
    HISTORY_LIMIT,
    OPT_LOCKOUT,
    OPT_MAX_FAILED,
    OPT_PULSE,
    SIGNAL_UPDATE,
)

_LOGGER = logging.getLogger(__name__)


def _norm_dt(value: Any) -> str | None:
    """Normalise a date string to UTC ISO format (naive input = HA time zone)."""
    if not value:
        return None
    parsed = dt_util.parse_datetime(str(value))
    if parsed is None:
        raise HomeAssistantError(f"Ungültiges Datum: {value}")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
    return dt_util.as_utc(parsed).isoformat()


class DoorCodeManager:
    """Manages codes, validates keypad input and opens the door."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._store: Store = Store(hass, 1, f"{DOMAIN}.codes")
        self.codes: dict[str, dict[str, Any]] = {}
        self.history: list[dict[str, Any]] = []
        self.status = "armed"
        self.failed = 0
        self.lockout_until = None
        self.last_used: str | None = None
        self._unsubs: list[CALLBACK_TYPE] = []
        self._cancel_reset: CALLBACK_TYPE | None = None

    # ---------- lifecycle ----------
    async def async_start(self) -> None:
        data = await self._store.async_load() or {}
        self.codes = data.get("codes", {})
        self.history = data.get("history", [])
        trigger = self.entry.data.get(CONF_TRIGGER)
        if trigger:
            # keypad publishes the PIN, then pulses a "code received" sensor
            self._unsubs.append(
                async_track_state_change_event(self.hass, [trigger], self._on_trigger)
            )
        else:
            self._unsubs.append(
                async_track_state_change_event(
                    self.hass, [self.entry.data[CONF_KEYPAD]], self._on_keypad
                )
            )
        # status of codes changes with time (scheduled -> active -> expired)
        self._unsubs.append(
            async_track_time_interval(
                self.hass, lambda _now: self._signal(), timedelta(minutes=1)
            )
        )

    async def async_stop(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        if self._cancel_reset:
            self._cancel_reset()
        await self._store.async_save(self._payload())

    def _payload(self) -> dict[str, Any]:
        return {"codes": self.codes, "history": self.history}

    def _signal(self) -> None:
        async_dispatcher_send(self.hass, SIGNAL_UPDATE)

    def _changed(self) -> None:
        self._store.async_delay_save(self._payload, 1)
        self._signal()

    def _opt(self, key: str, default: int) -> int:
        return int(self.entry.options.get(key, default))

    # ---------- state ----------
    def code_status(self, code: dict[str, Any], now=None) -> str:
        now = now or dt_util.utcnow()
        if code.get("used"):
            return "used"
        if not code.get("enabled", True):
            return "disabled"
        if code.get("valid_from") and now < dt_util.parse_datetime(code["valid_from"]):
            return "scheduled"
        if code.get("expires_at") and now > dt_util.parse_datetime(code["expires_at"]):
            return "expired"
        return "active"

    @property
    def active_count(self) -> int:
        now = dt_util.utcnow()
        return sum(1 for c in self.codes.values() if self.code_status(c, now) == "active")

    def _locked(self) -> bool:
        return self.lockout_until is not None and dt_util.utcnow() < self.lockout_until

    def snapshot(self) -> dict[str, Any]:
        now = dt_util.utcnow()
        codes = [{**c, "status": self.code_status(c, now)} for c in self.codes.values()]
        codes.sort(key=lambda c: c["name"].lower())
        return {
            "codes": codes,
            "history": self.history[:50],
            "status": self.status,
            "failed": self.failed,
            "lockout_until": self.lockout_until.isoformat() if self._locked() else None,
        }

    # ---------- CRUD ----------
    def _check(self, code: str, exclude: str | None = None) -> None:
        if not (code.isascii() and code.isdigit() and 4 <= len(code) <= 12):
            raise HomeAssistantError("Der Code muss aus 4 bis 12 Ziffern bestehen.")
        now = dt_util.utcnow()
        for cid, other in self.codes.items():
            if cid != exclude and other["code"].lstrip("0") == code.lstrip("0") and self.code_status(other, now) in (
                "active",
                "scheduled",
            ):
                raise HomeAssistantError("Dieser Code wird bereits für eine andere Person verwendet.")

    async def async_add(self, data: dict[str, Any]) -> dict[str, Any]:
        code = str(data["code"]).strip()
        self._check(code)
        cid = uuid.uuid4().hex[:8]
        self.codes[cid] = {
            "id": cid,
            "name": str(data["name"]).strip(),
            "code": code,
            "enabled": data.get("enabled", True),
            "one_time": data.get("one_time", False),
            "notify": data.get("notify", True),
            "valid_from": _norm_dt(data.get("valid_from")),
            "expires_at": _norm_dt(data.get("expires_at")),
            "created_at": dt_util.utcnow().isoformat(),
            "last_used": None,
            "use_count": 0,
            "used": False,
        }
        self.hass.bus.async_fire(EVENT_CODE_ADDED, {"code_id": cid, "name": self.codes[cid]["name"]})
        self._changed()
        return self.codes[cid]

    async def async_update(self, cid: str, changes: dict[str, Any]) -> dict[str, Any]:
        current = self.codes.get(cid)
        if current is None:
            raise HomeAssistantError("Code nicht gefunden.")
        new = {**current, **{k: v for k, v in changes.items() if k in EDITABLE}}
        for key in ("valid_from", "expires_at"):
            if key in changes:
                new[key] = _norm_dt(changes[key])
        if changes.get("enabled"):
            new["used"] = False  # re-enabling a spent one-time code revives it
        new["code"] = str(new["code"]).strip()
        new["name"] = str(new["name"]).strip()
        self._check(new["code"], exclude=cid)
        current.update(new)
        self._changed()
        return current

    async def async_delete(self, cid: str) -> None:
        code = self.codes.pop(cid, None)
        if code is None:
            raise HomeAssistantError("Code nicht gefunden.")
        self.hass.bus.async_fire(EVENT_CODE_DELETED, {"code_id": cid, "name": code["name"]})
        self._changed()

    # ---------- keypad ----------
    @callback
    def _on_keypad(self, event: Event) -> None:
        new = event.data.get("new_state")
        if new is None or new.state in ("", STATE_UNKNOWN, STATE_UNAVAILABLE):
            return
        self.hass.async_create_task(self._async_handle_input(self._normalize(new.state)))

    @callback
    def _on_trigger(self, event: Event) -> None:
        new, old = event.data.get("new_state"), event.data.get("old_state")
        if new is None or new.state != "on" or (old is not None and old.state == "on"):
            return
        pin = self.hass.states.get(self.entry.data[CONF_KEYPAD])
        if pin is None or pin.state in ("", STATE_UNKNOWN, STATE_UNAVAILABLE):
            return
        self.hass.async_create_task(self._async_handle_input(self._normalize(pin.state)))

    @staticmethod
    def _normalize(state: str) -> str:
        """Numeric sensors report '1234' or '1234.0' -> '1234'."""
        value = state.strip()
        try:
            number = float(value)
        except ValueError:
            return value
        return str(int(number)) if number.is_integer() else value

    @staticmethod
    def _matches(stored: str, entered: str) -> bool:
        # a numeric PIN sensor loses leading zeros ('0123' arrives as '123')
        return stored == entered or (
            not entered.startswith("0") and stored.lstrip("0") == entered
        )

    def _log(self, result: str, code: dict[str, Any] | None = None) -> None:
        self.history.insert(
            0,
            {
                "time": dt_util.utcnow().isoformat(),
                "result": result,
                "code_id": code["id"] if code else None,
                "name": code["name"] if code else None,
            },
        )
        del self.history[HISTORY_LIMIT:]

    def _flash(self, status: str, seconds: float) -> None:
        self.status = status
        if self._cancel_reset:
            self._cancel_reset()
        self._cancel_reset = async_call_later(self.hass, seconds, self._reset_status)
        self._changed()

    @callback
    def _reset_status(self, _now=None) -> None:
        self._cancel_reset = None
        if not self._locked():
            self.lockout_until = None
        self.status = "locked_out" if self._locked() else "armed"
        self._signal()

    async def _async_handle_input(self, entered: str) -> None:
        if self._locked():
            self._log("lockout")
            self._changed()
            return
        now = dt_util.utcnow()
        for code in self.codes.values():
            if self._matches(code["code"], entered) and self.code_status(code, now) == "active":
                await self._grant(code, now)
                return
        self._deny()

    async def _grant(self, code: dict[str, Any], now) -> None:
        code["last_used"] = now.isoformat()
        code["use_count"] = code.get("use_count", 0) + 1
        if code.get("one_time"):
            code["used"] = True
        self.failed = 0
        self.last_used = code["name"]
        self._log("granted", code)
        self.hass.bus.async_fire(
            EVENT_CODE_USED,
            {"code_id": code["id"], "name": code["name"], "use_count": code["use_count"]},
        )
        self._flash("code_accepted", 2)
        await self._open_door()
        if code.get("notify", True):
            await self._notify(code)

    def _deny(self) -> None:
        self.failed += 1
        self._log("denied")
        self.hass.bus.async_fire(EVENT_INVALID_CODE, {"failed_attempts": self.failed})
        if self.failed >= self._opt(OPT_MAX_FAILED, DEFAULT_MAX_FAILED):
            duration = self._opt(OPT_LOCKOUT, DEFAULT_LOCKOUT)
            self.lockout_until = dt_util.utcnow() + timedelta(seconds=duration)
            self.failed = 0
            self.hass.bus.async_fire(EVENT_LOCKOUT, {"duration": duration})
            self._flash("locked_out", duration)
        else:
            self._flash("code_rejected", 2)

    async def _open_door(self) -> None:
        entity = self.entry.data[CONF_DOOR]
        domain = entity.split(".")[0]
        try:
            if domain == "button":
                await self.hass.services.async_call("button", "press", {"entity_id": entity})
            elif domain == "lock":
                await self.hass.services.async_call("lock", "unlock", {"entity_id": entity})
            else:
                await self.hass.services.async_call(domain, "turn_on", {"entity_id": entity})

                async def _off(_now) -> None:
                    await self.hass.services.async_call(domain, "turn_off", {"entity_id": entity})

                async_call_later(self.hass, self._opt(OPT_PULSE, DEFAULT_PULSE), _off)
        except HomeAssistantError:
            _LOGGER.exception("Türöffner %s konnte nicht angesteuert werden", entity)

    async def _notify(self, code: dict[str, Any]) -> None:
        target = (self.entry.data.get(CONF_NOTIFY) or "").removeprefix("notify.")
        if not target or not self.hass.services.has_service("notify", target):
            return
        await self.hass.services.async_call(
            "notify",
            target,
            {"title": "Tür geöffnet", "message": f"{code['name']} hat die Tür geöffnet."},
        )
