DOMAIN = "awtrix_blueprint_migrator"
SERVICE_MIGRATE = "migrate"

CONF_AUTOMATIONS = "automations"
CONF_TARGET_AWTRIX_DEVICE = "target_awtrix_device"
CONF_NAME_PREFIX = "name_prefix"
CONF_DISABLE_ORIGINALS = "disable_originals"
CONF_DRY_RUN = "dry_run"
CONF_SKIP_EXISTING = "skip_existing"

DEFAULT_NAME_PREFIX = "[NG] "

TARGET_BLUEPRINT_PATH = (
    "awtrix_blueprint_migrator/awtrix_ng_layout_app_extended.yaml"
)
TARGET_BLUEPRINT_FILENAME = "awtrix_ng_layout_app_extended.yaml"

MIGRATION_MARKER_PREFIX = "awtrix_blueprint_migrator_source="
