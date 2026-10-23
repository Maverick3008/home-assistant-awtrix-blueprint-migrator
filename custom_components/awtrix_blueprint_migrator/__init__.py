"""AWTRIX Blueprint Migrator integration."""

from __future__ import annotations

import asyncio
from pathlib import Path
import shutil
from typing import TYPE_CHECKING, Any

from .const import (
    CONF_AUTOMATIONS,
    CONF_DISABLE_ORIGINALS,
    CONF_DRY_RUN,
    CONF_NAME_PREFIX,
    CONF_SKIP_EXISTING,
    CONF_TARGET_AWTRIX_DEVICE,
    DEFAULT_NAME_PREFIX,
    DOMAIN,
    SERVICE_MIGRATE,
    TARGET_BLUEPRINT_FILENAME,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_DATA_LOCK = "migration_lock"
_DATA_REGISTERED = "service_registered"


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


def _build_migrate_schema(has_default_target: bool) -> Any:
    """Build the service schema lazily.

    Keeping Home Assistant and voluptuous imports out of module import time is
    intentional. Home Assistant imports the package __init__.py before
    config_flow.py; a volatile internal import here would otherwise make the
    UI report only 'Invalid handler specified'.
    """
    import voluptuous as vol

    from homeassistant.helpers import config_validation as cv

    target_field = (
        vol.Optional(CONF_TARGET_AWTRIX_DEVICE)
        if has_default_target
        else vol.Required(CONF_TARGET_AWTRIX_DEVICE)
    )

    return vol.Schema(
        {
            vol.Required(CONF_AUTOMATIONS): cv.entity_ids,
            target_field: cv.string,
            vol.Optional(CONF_NAME_PREFIX): cv.string,
            vol.Optional(CONF_DISABLE_ORIGINALS, default=False): cv.boolean,
            vol.Optional(CONF_SKIP_EXISTING, default=True): cv.boolean,
            vol.Optional(CONF_DRY_RUN, default=False): cv.boolean,
        }
    )


async def _async_notify_error(hass: HomeAssistant, message: str) -> None:
    """Expose migration errors in the UI instead of only 'Unknown error'."""
    await hass.services.async_call(
        "persistent_notification",
        "create",
        {
            "title": "AWTRIX Blueprint Migrator – Fehler",
            "message": message,
            "notification_id": "awtrix_blueprint_migrator_last_error",
        },
        blocking=False,
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AWTRIX Blueprint Migrator."""
    # Import HA automation internals only after the config flow has created the
    # entry. This keeps config_flow.py independent from migration internals.
    from homeassistant.components import automation
    from homeassistant.core import ServiceCall

    from .migration import async_migrate, async_notify_result

    await hass.async_add_executor_job(_install_bundled_blueprint, hass.config.config_dir)

    # Refresh Home Assistant's automation-blueprint cache if the API is
    # available. The blueprint file itself is already installed even if this
    # optional refresh fails on another HA release.
    try:
        blueprints = automation.async_get_blueprints(hass)
        await blueprints.async_populate()
    except (AttributeError, ImportError):
        pass

    data = hass.data.setdefault(DOMAIN, {})
    data.setdefault(_DATA_LOCK, asyncio.Lock())

    if not data.get(_DATA_REGISTERED):

        async def handle_migrate(call: ServiceCall) -> None:
            from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

            async with data[_DATA_LOCK]:
                try:
                    target_awtrix_device = call.data.get(
                        CONF_TARGET_AWTRIX_DEVICE,
                        entry.data.get(CONF_TARGET_AWTRIX_DEVICE),
                    )
                    if not target_awtrix_device:
                        raise HomeAssistantError(
                            "Kein AWTRIX-Zielgerät konfiguriert. "
                            "Bitte Integration neu einrichten oder Zielgerät in der Aktion angeben."
                        )

                    result = await async_migrate(
                        hass,
                        list(call.data[CONF_AUTOMATIONS]),
                        target_awtrix_device=target_awtrix_device,
                        name_prefix=call.data.get(
                            CONF_NAME_PREFIX,
                            entry.data.get(CONF_NAME_PREFIX, DEFAULT_NAME_PREFIX),
                        ),
                        disable_originals=call.data[CONF_DISABLE_ORIGINALS],
                        skip_existing=call.data[CONF_SKIP_EXISTING],
                        dry_run=call.data[CONF_DRY_RUN],
                    )
                    await async_notify_result(hass, result)
                except ServiceValidationError:
                    raise
                except HomeAssistantError as err:
                    await _async_notify_error(hass, str(err))
                    raise ServiceValidationError(str(err)) from err
                except Exception as err:
                    import logging

                    logging.getLogger(__name__).exception(
                        "Unexpected error during AWTRIX blueprint migration"
                    )
                    message = f"{type(err).__name__}: {err}"
                    await _async_notify_error(hass, message)
                    raise ServiceValidationError(
                        f"AWTRIX-Migration fehlgeschlagen: {message}"
                    ) from err

        hass.services.async_register(
            DOMAIN,
            SERVICE_MIGRATE,
            handle_migrate,
            schema=_build_migrate_schema(CONF_TARGET_AWTRIX_DEVICE in entry.data),
        )
        data[_DATA_REGISTERED] = True

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the integration."""
    if hass.services.has_service(DOMAIN, SERVICE_MIGRATE):
        hass.services.async_remove(DOMAIN, SERVICE_MIGRATE)
    hass.data.pop(DOMAIN, None)
    return True
