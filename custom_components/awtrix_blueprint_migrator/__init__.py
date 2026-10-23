"""AWTRIX Blueprint Migrator integration."""

from __future__ import annotations

import asyncio
from pathlib import Path
import shutil

import voluptuous as vol

from homeassistant.components.automation.helpers import async_get_blueprints
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_AUTOMATIONS,
    CONF_TARGET_AWTRIX_DEVICE,
    CONF_DISABLE_ORIGINALS,
    CONF_DRY_RUN,
    CONF_NAME_PREFIX,
    CONF_SKIP_EXISTING,
    DEFAULT_NAME_PREFIX,
    DOMAIN,
    SERVICE_MIGRATE,
    TARGET_BLUEPRINT_FILENAME,
)
from .migration import async_migrate, notify_result

_DATA_LOCK = "migration_lock"
_DATA_REGISTERED = "service_registered"

MIGRATE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_AUTOMATIONS): cv.entity_ids,
        vol.Required(CONF_TARGET_AWTRIX_DEVICE): cv.string,
        vol.Optional(CONF_NAME_PREFIX, default=DEFAULT_NAME_PREFIX): cv.string,
        vol.Optional(CONF_DISABLE_ORIGINALS, default=False): cv.boolean,
        vol.Optional(CONF_SKIP_EXISTING, default=True): cv.boolean,
        vol.Optional(CONF_DRY_RUN, default=False): cv.boolean,
    }
)


def _install_bundled_blueprint(config_dir: str) -> None:
    """Install/update the bundled target blueprint."""
    source = Path(__file__).with_name("blueprint.yaml")
    target_dir = (
        Path(config_dir)
        / "blueprints"
        / "automation"
        / "awtrix_blueprint_migrator"
    )
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / TARGET_BLUEPRINT_FILENAME

    source_bytes = source.read_bytes()
    if target.exists() and target.read_bytes() == source_bytes:
        return

    if target.exists():
        backup = target.with_suffix(target.suffix + ".bak")
        shutil.copy2(target, backup)

    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_bytes(source_bytes)
    tmp.replace(target)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AWTRIX Blueprint Migrator."""
    await hass.async_add_executor_job(_install_bundled_blueprint, hass.config.config_dir)
    await async_get_blueprints(hass).async_populate()

    data = hass.data.setdefault(DOMAIN, {})
    data.setdefault(_DATA_LOCK, asyncio.Lock())

    if not data.get(_DATA_REGISTERED):

        async def handle_migrate(call: ServiceCall) -> None:
            async with data[_DATA_LOCK]:
                result = await async_migrate(
                    hass,
                    list(call.data[CONF_AUTOMATIONS]),
                    target_awtrix_device=call.data[CONF_TARGET_AWTRIX_DEVICE],
                    name_prefix=call.data[CONF_NAME_PREFIX],
                    disable_originals=call.data[CONF_DISABLE_ORIGINALS],
                    skip_existing=call.data[CONF_SKIP_EXISTING],
                    dry_run=call.data[CONF_DRY_RUN],
                )
                notify_result(hass, result)

        hass.services.async_register(
            DOMAIN,
            SERVICE_MIGRATE,
            handle_migrate,
            schema=MIGRATE_SCHEMA,
        )
        data[_DATA_REGISTERED] = True

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the integration."""
    # Single-instance integration: remove the service when unloaded.
    if hass.services.has_service(DOMAIN, SERVICE_MIGRATE):
        hass.services.async_remove(DOMAIN, SERVICE_MIGRATE)
    hass.data.pop(DOMAIN, None)
    return True
