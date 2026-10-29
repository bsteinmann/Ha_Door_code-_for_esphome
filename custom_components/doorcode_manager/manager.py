"""Core logic of Door Code Manager."""
from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Callable
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import label_registry as lr
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify

from .const import (
    ACTION_DOMAINS,
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
    OPT_ACTION_LABEL,
    OPT_LOCKOUT,
    OPT_MAX_FAILED,
    OPT_NOTIFY_DEFAULT,
    OPT_PULSE,
    OPT_TAG_DEVICES,
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


def _norm_tags(tags: Any) -> list[str]:
    out: list[str] = []
    for tag in tags or []:
        tag = str(tag).strip()
        if tag and tag.casefold() not in [t.casefold() for t in out]:
            out.append(tag)
    return out


def _norm_actions(actions: Any) -> list[str]:
    out: list[str] = []
    for action in actions or []:
        action = str(action).strip()
        if not action:
            continue
        if "." not in action or action.split(".", 1)[0] not in ACTION_DOMAINS:
            raise HomeAssistantError(f"Diese Aktion ist nicht erlaubt: {action}")
        if action not in out:
            out.append(action)
    return out


class DoorCodeManager:
    """Manages persons (PIN and/or NFC tags), validates input, opens the door."""

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
        self._learn: asyncio.Future | None = None

    # ---------- lifecycle ----------
    async def async_start(self) -> None:
        data = await self._store.async_load() or {}
        self.codes = data.get("codes", {})
        self.history = data.get("history", [])
        trigger = self.entry.data.get(CONF_TRIGGER)
        if trigger:
            self._unsubs.append(
                async_track_state_change_event(self.hass, [trigger], self._on_trigger)
            )
        else:
            self._unsubs.append(
                async_track_state_change_event(
                    self.hass, [self.entry.data[CONF_KEYPAD]], self._on_keypad
                )
            )
        self._unsubs.append(self.hass.bus.async_listen("tag_scanned", self._on_tag))
        self._unsubs.append(
            async_track_time_interval(
                self.hass, lambda _now: self._signal(), timedelta(minutes=1)
            )
        )

    async def async_stop(self) -> None:
        self.cancel_learn()
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

    def notify_targets(self) -> list[dict[str, str]]:
        """Notify services of devices running the companion app, labelled with the person."""
        reg = self.hass.services
        try:
            services = reg.async_services_for_domain("notify")
        except AttributeError:  # older HA
            services = reg.async_services().get("notify", {})

        owners: dict[str, str] = {}
        for state in self.hass.states.async_all("person"):
            for tracker in state.attributes.get("device_trackers", []) or []:
                owners[tracker.split(".", 1)[-1]] = state.name

        labels: dict[str, str] = {}
        for entry in self.hass.config_entries.async_entries("mobile_app"):
            device = entry.data.get("device_name") or entry.title
            slug = slugify(device)
            person = owners.get(slug)
            labels[f"mobile_app_{slug}"] = f"{person} ({device})" if person else device

        result = [
            {"service": s, "label": labels.get(s, s.removeprefix("mobile_app_"))}
            for s in sorted(services)
            if s.startswith("mobile_app_")
        ]
        result.sort(key=lambda r: r["label"].lower())
        return result

    def action_entities(self) -> dict[str, Any]:
        """Entities offered as actions: only those carrying the configured label."""
        label_id = self.entry.options.get(OPT_ACTION_LABEL)
        if not label_id:
            return {"label": None, "entities": []}
        label = lr.async_get(self.hass).async_get_label(label_id)
        entities = []
        for entry in er.async_get(self.hass).entities.values():
            if label_id not in entry.labels or entry.disabled_by or entry.domain not in ACTION_DOMAINS:
                continue
            state = self.hass.states.get(entry.entity_id)
            name = (state.name if state else None) or entry.name or entry.original_name or entry.entity_id
            entities.append({"entity_id": entry.entity_id, "name": name, "domain": entry.domain})
        entities.sort(key=lambda e: (e["domain"], e["name"].lower()))
        return {"label": label.name if label else label_id, "entities": entities}

    # ---------- NFC learning ----------
    async def async_learn_tag(self, timeout: float = 30) -> str:
        if self._learn is not None and not self._learn.done():
            raise HomeAssistantError("Es läuft bereits ein Anlernvorgang.")
        self._learn = self.hass.loop.create_future()
        try:
            return await asyncio.wait_for(self._learn, timeout)
        except asyncio.TimeoutError as err:
            raise HomeAssistantError("Kein Tag erkannt (Zeitüberschreitung).") from err
        finally:
            self._learn = None

    @callback
    def cancel_learn(self) -> None:
        if self._learn is not None and not self._learn.done():
            self._learn.set_exception(HomeAssistantError("Anlernen abgebrochen."))

    # ---------- CRUD ----------
    def _check(self, code: str | None, tags: list[str], exclude: str | None = None) -> None:
        if not code and not tags:
            raise HomeAssistantError("Bitte einen PIN-Code oder mindestens einen NFC-Tag angeben.")
        now = dt_util.utcnow()
        if code:
            if not (code.isascii() and code.isdigit() and 4 <= len(code) <= 12):
                raise HomeAssistantError("Der Code muss aus 4 bis 12 Ziffern bestehen.")
            for cid, other in self.codes.items():
                if (
                    cid != exclude
                    and other.get("code")
                    and other["code"].lstrip("0") == code.lstrip("0")
                    and self.code_status(other, now) in ("active", "scheduled")
                ):
                    raise HomeAssistantError("Dieser Code wird bereits für eine andere Person verwendet.")
        mine = {t.casefold() for t in tags}
        for cid, other in self.codes.items():
            if cid != exclude and mine & {t.casefold() for t in other.get("tags", [])}:
                raise HomeAssistantError("Dieser NFC-Tag ist bereits einer anderen Person zugeordnet.")

    async def async_add(self, data: dict[str, Any]) -> dict[str, Any]:
        code = str(data["code"]).strip() if data.get("code") else None
        tags = _norm_tags(data.get("tags"))
        actions = _norm_actions(data.get("actions"))
        kind = data.get("kind", "person")
        if kind not in ("person", "action"):
            raise HomeAssistantError("Unbekannte Art des Eintrags.")
        open_door = False if kind == "action" else data.get("open_door", True)
        if kind == "action" and not actions:
            raise HomeAssistantError("Bitte mindestens eine Aktion wählen.")
        if not open_door and not actions:
            raise HomeAssistantError("Bitte „Tür öffnen“ aktivieren oder mindestens eine Aktion wählen.")
        self._check(code, tags)
        cid = uuid.uuid4().hex[:8]
        self.codes[cid] = {
            "id": cid,
            "name": str(data["name"]).strip(),
            "code": code,
            "kind": kind,
            "tags": tags,
            "open_door": open_door,
            "actions": actions,
            "enabled": data.get("enabled", True),
            "one_time": data.get("one_time", False),
            "notify": data.get("notify", True),
            "notify_targets": list(data.get("notify_targets") or []),
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
            raise HomeAssistantError("Eintrag nicht gefunden.")
        new = {**current, **{k: v for k, v in changes.items() if k in EDITABLE}}
        for key in ("valid_from", "expires_at"):
            if key in changes:
                new[key] = _norm_dt(changes[key])
        if changes.get("enabled"):
            new["used"] = False  # re-enabling a spent one-time entry revives it
        new["code"] = str(new["code"]).strip() if new.get("code") else None
        new["tags"] = _norm_tags(new.get("tags"))
        new["actions"] = _norm_actions(new.get("actions"))
        if current.get("kind", "person") == "action":
            new["open_door"] = False
            if not new["actions"]:
                raise HomeAssistantError("Bitte mindestens eine Aktion wählen.")
        else:
            new["open_door"] = new.get("open_door", True)
            if not new["open_door"] and not new["actions"]:
                raise HomeAssistantError("Bitte „Tür öffnen“ aktivieren oder mindestens eine Aktion wählen.")
        new["notify_targets"] = list(new.get("notify_targets") or [])
        new["name"] = str(new["name"]).strip()
        self._check(new["code"], new["tags"], exclude=cid)
        current.update(new)
        self._changed()
        return current

    async def async_delete(self, cid: str) -> None:
        code = self.codes.pop(cid, None)
        if code is None:
            raise HomeAssistantError("Eintrag nicht gefunden.")
        self.hass.bus.async_fire(EVENT_CODE_DELETED, {"code_id": cid, "name": code["name"]})
        self._changed()

    # ---------- inputs ----------
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

    @callback
    def _on_tag(self, event: Event) -> None:
        tag_id = event.data.get("tag_id")
        if not tag_id:
            return
        if self._learn is not None and not self._learn.done():
            self._learn.set_result(str(tag_id))  # consumed by "learn" mode, door stays shut
            return
        allowed = self.entry.options.get(OPT_TAG_DEVICES) or []
        if allowed and event.data.get("device_id") not in allowed:
            return
        self.hass.async_create_task(self._async_handle_tag(str(tag_id)))

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
        # a numeric PIN sensor loses leading zeros ('0123' -> '123', '0000' -> '0')
        if stored == entered:
            return True
        return entered.isdigit() and stored.lstrip("0") == entered.lstrip("0")

    async def _async_handle_input(self, entered: str) -> None:
        await self._attempt(
            "pin", lambda c: bool(c.get("code")) and self._matches(c["code"], entered)
        )

    async def _async_handle_tag(self, tag_id: str) -> None:
        key = tag_id.casefold()
        await self._attempt(
            "nfc", lambda c: key in [t.casefold() for t in c.get("tags", [])]
        )

    async def _attempt(self, method: str, match: Callable[[dict[str, Any]], bool]) -> None:
        if self._locked():
            self._log("lockout", method=method)
            self._changed()
            return
        now = dt_util.utcnow()
        for code in self.codes.values():
            if match(code) and self.code_status(code, now) == "active":
                await self._grant(code, now, method)
                return
        self._deny(method)

    def _log(self, result: str, code: dict[str, Any] | None = None, method: str | None = None) -> None:
        self.history.insert(
            0,
            {
                "time": dt_util.utcnow().isoformat(),
                "result": result,
                "method": method,
                "kind": code.get("kind", "person") if code else None,
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

    async def _grant(self, code: dict[str, Any], now, method: str) -> None:
        code["last_used"] = now.isoformat()
        code["use_count"] = code.get("use_count", 0) + 1
        if code.get("one_time"):
            code["used"] = True
        self.failed = 0
        self.last_used = code["name"]
        self._log("granted", code, method)
        self.hass.bus.async_fire(
            EVENT_CODE_USED,
            {
                "code_id": code["id"],
                "name": code["name"],
                "use_count": code["use_count"],
                "kind": code.get("kind", "person"),
                "method": method,
            },
        )
        self._flash("code_accepted", 2)
        if code.get("open_door", True):
            await self._open_door()
        await self._run_actions(code, method)
        if code.get("notify", True):
            await self._notify(code, method)

    def _deny(self, method: str) -> None:
        self.failed += 1
        self._log("denied", method=method)
        self.hass.bus.async_fire(
            EVENT_INVALID_CODE, {"failed_attempts": self.failed, "method": method}
        )
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

    async def _run_actions(self, code: dict[str, Any], method: str) -> None:
        variables = {"person": code["name"], "code_id": code["id"], "method": method}
        for entity in code.get("actions", []):
            if self.hass.states.get(entity) is None:
                _LOGGER.warning("Aktion %s existiert nicht mehr", entity)
                continue
            domain = entity.split(".", 1)[0]
            data: dict[str, Any] = {"entity_id": entity}
            if domain == "script":
                service = ("script", "turn_on")
                data["variables"] = variables
            elif domain == "scene":
                service = ("scene", "turn_on")
            elif domain == "automation":
                service = ("automation", "trigger")
                data["skip_condition"] = True
            elif domain in ("button", "input_button"):
                service = (domain, "press")
            elif domain == "lock":
                service = ("lock", "unlock")
            elif domain == "cover":
                service = ("cover", "open_cover")
            else:
                service = ("homeassistant", "turn_on")
            try:
                await self.hass.services.async_call(*service, data)
            except HomeAssistantError:
                _LOGGER.exception("Aktion %s fehlgeschlagen", entity)

    async def _notify(self, code: dict[str, Any], method: str) -> None:
        targets = (
            code.get("notify_targets")
            or self.entry.options.get(OPT_NOTIFY_DEFAULT)
            or ([self.entry.data[CONF_NOTIFY]] if self.entry.data.get(CONF_NOTIFY) else [])
        )
        how = "NFC-Tag" if method == "nfc" else "PIN"
        if code.get("kind", "person") == "action":
            title, message = "Aktion ausgelöst", f"{code['name']} wurde per {how} ausgelöst."
        else:
            title, message = "Tür geöffnet", f"{code['name']} hat die Tür geöffnet ({how})."
        for target in targets:
            service = target.removeprefix("notify.")
            if not self.hass.services.has_service("notify", service):
                continue
            try:
                await self.hass.services.async_call(
                    "notify",
                    service,
                    {"title": title, "message": message},
                )
            except HomeAssistantError:
                _LOGGER.warning("Benachrichtigung über notify.%s fehlgeschlagen", service)
