"""Constants for Door Code Manager."""

DOMAIN = "doorcode_manager"
VERSION = "2.2.0"

SIGNAL_UPDATE = f"{DOMAIN}_update"
PANEL_URL = f"/{DOMAIN}/doorcode-panel.js"
PANEL_PATH = "doorcode"

CONF_KEYPAD = "keypad_entity"
CONF_DOOR = "door_opener_entity"
CONF_TRIGGER = "trigger_entity"
CONF_NOTIFY = "notification_target"

OPT_PULSE = "auto_lock_delay"
OPT_MAX_FAILED = "failed_attempts_threshold"
OPT_LOCKOUT = "lockout_duration"
OPT_TAG_DEVICES = "tag_devices"
OPT_NOTIFY_DEFAULT = "default_notify_targets"
DEFAULT_PULSE = 3
DEFAULT_MAX_FAILED = 5
DEFAULT_LOCKOUT = 60

EVENT_CODE_USED = f"{DOMAIN}_code_used"
EVENT_CODE_ADDED = f"{DOMAIN}_code_added"
EVENT_CODE_DELETED = f"{DOMAIN}_code_deleted"
EVENT_INVALID_CODE = f"{DOMAIN}_invalid_code"
EVENT_LOCKOUT = f"{DOMAIN}_lockout_started"

HISTORY_LIMIT = 100
ACTION_DOMAINS = (
    "script", "scene", "automation", "button", "input_button",
    "switch", "light", "input_boolean", "lock", "cover",
)
EDITABLE = (
    "name", "code", "tags", "open_door", "actions", "enabled", "one_time", "notify", "notify_targets", "valid_from", "expires_at",
)
