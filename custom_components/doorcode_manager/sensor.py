"""Sensors for Door Code Manager."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_UPDATE
from .manager import DoorCodeManager


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    manager: DoorCodeManager = hass.data[DOMAIN]
    async_add_entities(
        [
            StatusSensor(manager, entry),
            LastUsedSensor(manager, entry),
            ActiveCodesSensor(manager, entry),
        ]
    )


class _Base(SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, manager: DoorCodeManager, entry: ConfigEntry, key: str, name: str) -> None:
        self._manager = manager
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)}, name="Door Code Manager"
        )

    async def async_added_to_hass(self) -> None:
        @callback
        def _update() -> None:
            self.async_write_ha_state()

        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_UPDATE, _update))


class StatusSensor(_Base):
    """armed / code_accepted / code_rejected / locked_out"""

    _attr_icon = "mdi:dialpad"

    def __init__(self, manager, entry) -> None:
        super().__init__(manager, entry, "status", "Status")

    @property
    def native_value(self) -> str:
        return self._manager.status


class LastUsedSensor(_Base):
    _attr_icon = "mdi:account-clock"

    def __init__(self, manager, entry) -> None:
        super().__init__(manager, entry, "last_used", "Zuletzt verwendet")

    @property
    def native_value(self) -> str | None:
        return self._manager.last_used


class ActiveCodesSensor(_Base):
    _attr_icon = "mdi:key-chain"

    def __init__(self, manager, entry) -> None:
        super().__init__(manager, entry, "active_codes", "Aktive Codes")

    @property
    def native_value(self) -> int:
        return self._manager.active_count

    @property
    def extra_state_attributes(self) -> dict[str, int]:
        return {"total": len(self._manager.codes)}
