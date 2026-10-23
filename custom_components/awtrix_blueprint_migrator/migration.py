"""Migration helpers for AWTRIX Blueprint Migrator."""

from __future__ import annotations

import copy
from datetime import datetime
import logging
import os
import shutil
from typing import Any, TYPE_CHECKING
import uuid

from .const import MIGRATION_MARKER_PREFIX, TARGET_BLUEPRINT_PATH

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


def _as_list(value: Any) -> list[Any]:
    """Return value as list without changing existing lists."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _as_text(value: Any) -> str:
    """Convert legacy prefix/suffix values to text safely."""
    if value is None:
        return ""
    return value if isinstance(value, str) else str(value)


def _read_automations_file(path: str) -> list[dict[str, Any]]:
    """Read automations.yaml."""
    from homeassistant.exceptions import HomeAssistantError
    from homeassistant.util.yaml import load_yaml

    if not os.path.isfile(path):
        return []

    data = load_yaml(path)
    if data is None:
        return []
    if not isinstance(data, list):
        raise HomeAssistantError(
            "automations.yaml enthält keine Liste. Die Migration wurde abgebrochen."
        )
    return data


def _write_automations_file(path: str, data: list[dict[str, Any]]) -> None:
    """Atomically write automations.yaml using Home Assistant YAML helpers."""
    from homeassistant.util.file import write_utf8_file_atomic
    from homeassistant.util.yaml import dump

    contents = dump(data)
    write_utf8_file_atomic(path, contents)


def _create_backup(path: str, config_dir: str) -> str | None:
    """Create a timestamped backup of automations.yaml."""
    if not os.path.isfile(path):
        return None

    backup_dir = os.path.join(config_dir, ".awtrix_blueprint_migrator_backups")
    os.makedirs(backup_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"automations_{stamp}.yaml")
    shutil.copy2(path, backup_path)
    return backup_path


def _migration_marker(source_key: str) -> str:
    return f"{MIGRATION_MARKER_PREFIX}{source_key}"


def _already_migrated(
    automations_data: list[dict[str, Any]], source_key: str
) -> bool:
    """Check whether this source was already copied by us."""
    marker = _migration_marker(source_key)
    for item in automations_data:
        if not isinstance(item, dict):
            continue
        description = item.get("description")
        if isinstance(description, str) and marker in description:
            return True
    return False


def _find_source_raw_config(
    hass: HomeAssistant,
    entity_id: str,
    automations_data: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return the original automation config from automations.yaml.

    Home Assistant stores the automation ``id`` as the entity registry
    ``unique_id``.  Using the registry avoids depending on the private
    automation EntityComponent / DATA_COMPONENT internals, which have moved
    between Home Assistant releases.
    """
    from homeassistant.exceptions import HomeAssistantError
    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    registry_entry = registry.async_get(entity_id)

    source_id: str | None = None
    if registry_entry is not None and registry_entry.unique_id:
        source_id = str(registry_entry.unique_id)

    if source_id is not None:
        for item in automations_data:
            if not isinstance(item, dict):
                continue
            item_id = item.get("id")
            if item_id is not None and str(item_id) == source_id:
                return item

    # Conservative fallback for unusual/older registry states: match the
    # current Home Assistant display name to an alias, but only when unique.
    state = hass.states.get(entity_id)
    if state is not None and state.name:
        matches = [
            item
            for item in automations_data
            if isinstance(item, dict)
            and isinstance(item.get("alias"), str)
            and item.get("alias") == state.name
        ]
        if len(matches) == 1:
            return matches[0]

    if registry_entry is None:
        detail = "kein Entity-Registry-Eintrag gefunden"
    elif source_id is None:
        detail = "Entity-Registry-Eintrag hat keine unique_id"
    else:
        detail = f"Automation-ID {source_id!r} nicht in automations.yaml gefunden"

    raise HomeAssistantError(
        f"{entity_id}: Die Originalkonfiguration konnte nicht gefunden werden "
        f"({detail}). Die Automation muss in automations.yaml gespeichert sein."
    )


def _source_alias(hass: HomeAssistant, entity_id: str, raw: dict[str, Any]) -> str:
    """Get a human-friendly source alias."""
    alias = raw.get("alias")
    if isinstance(alias, str) and alias.strip():
        return alias.strip()

    state = hass.states.get(entity_id)
    if state is not None and state.name:
        return state.name
    return entity_id


def _map_legacy_inputs(
    old_inputs: dict[str, Any],
    target_awtrix_device: str,
) -> tuple[dict[str, Any], list[str]]:
    """Map legacy AWTRIX blueprint inputs to the NG blueprint."""
    from homeassistant.exceptions import HomeAssistantError

    warnings: list[str] = []

    if "entity" in old_inputs:
        entities = _as_list(copy.deepcopy(old_inputs.get("entity")))
    else:
        entities = _as_list(copy.deepcopy(old_inputs.get("entities")))

    if not entities:
        raise HomeAssistantError("Die alte Automation enthält keine Entität.")

    new_inputs: dict[str, Any] = {
        "app_name": copy.deepcopy(old_inputs.get("app_name", "awtrix_app")),
        "layout": "icon_value",
        "entities": entities,
        "icon": copy.deepcopy(old_inputs.get("app_icon", old_inputs.get("icon", ""))),
        "prefix_text": _as_text(old_inputs.get("prefix_text", "")),
        "suffix_text": _as_text(old_inputs.get("suffix_text", "")),
        "extra_triggers": copy.deepcopy(old_inputs.get("extra_triggers", [])) or [],
        "pre_actions": copy.deepcopy(old_inputs.get("pre_actions", [])) or [],
        "additional_conditions": copy.deepcopy(
            old_inputs.get("additional_conditions", [])
        )
        or [],
        "remove_when_conditions_false": True,
        "user_options": copy.deepcopy(old_inputs.get("user_options", {})) or {},
        # Always replace the legacy AWTRIX device with the explicitly selected
        # AWTRIX NG target device.
        "awtrix_device": [target_awtrix_device],
    }

    additional_options = old_inputs.get("additional_options", {}) or {}
    if isinstance(additional_options, dict):
        if "value_template" in additional_options:
            new_inputs["value_template"] = copy.deepcopy(
                additional_options["value_template"]
            )
        if "icon_template" in additional_options:
            new_inputs["icon_template"] = copy.deepcopy(
                additional_options["icon_template"]
            )

        known = {"value_template", "icon_template"}
        unknown = sorted(str(key) for key in additional_options if key not in known)
        if unknown:
            warnings.append(
                "Nicht zugeordnete additional_options: " + ", ".join(unknown)
            )
    elif additional_options:
        warnings.append("additional_options war kein Objekt und wurde übersprungen.")

    return new_inputs, warnings


def _build_new_automation(
    hass: HomeAssistant,
    source_entity_id: str,
    source_raw: dict[str, Any],
    old_inputs: dict[str, Any],
    name_prefix: str,
    target_awtrix_device: str,
) -> tuple[str, dict[str, Any], list[str]]:
    """Build one target blueprint automation."""
    source_key = str(source_raw.get("id") or source_entity_id)
    alias = f"{name_prefix}{_source_alias(hass, source_entity_id, source_raw)}"
    new_inputs, warnings = _map_legacy_inputs(old_inputs, target_awtrix_device)

    old_description = source_raw.get("description")
    description_parts: list[str] = []
    if isinstance(old_description, str) and old_description.strip():
        description_parts.append(old_description.strip())
    description_parts.append(
        "Kopie für AWTRIX NG, erstellt durch AWTRIX Blueprint Migrator."
    )
    description_parts.append(_migration_marker(source_key))

    new_id = uuid.uuid4().hex
    new_config: dict[str, Any] = {
        "id": new_id,
        "alias": alias,
        "description": "\n\n".join(description_parts),
        "use_blueprint": {
            "path": TARGET_BLUEPRINT_PATH,
            "input": new_inputs,
        },
    }
    return source_key, new_config, warnings


async def async_migrate(
    hass: HomeAssistant,
    entity_ids: list[str],
    *,
    target_awtrix_device: str,
    name_prefix: str,
    disable_originals: bool,
    skip_existing: bool,
    dry_run: bool,
) -> dict[str, Any]:
    """Migrate selected legacy AWTRIX automations."""
    from homeassistant.components import automation
    from homeassistant.components.automation.config import async_validate_config_item
    from homeassistant.config import AUTOMATION_CONFIG_PATH
    from homeassistant.const import ATTR_ENTITY_ID, SERVICE_RELOAD, SERVICE_TURN_OFF
    from homeassistant.exceptions import HomeAssistantError
    from homeassistant.helpers import device_registry as dr

    device_registry = dr.async_get(hass)
    target_device = device_registry.async_get(target_awtrix_device)
    if target_device is None:
        raise HomeAssistantError(
            f"Das ausgewählte AWTRIX-Zielgerät wurde nicht gefunden: {target_awtrix_device}"
        )
    if target_device.manufacturer and target_device.manufacturer != "Blueforcer":
        raise HomeAssistantError(
            "Das ausgewählte Zielgerät ist kein Blueforcer/AWTRIX-Gerät."
        )

    automations_path = hass.config.path(AUTOMATION_CONFIG_PATH)
    current = await hass.async_add_executor_job(_read_automations_file, automations_path)

    planned: list[tuple[str, dict[str, Any]]] = []
    skipped: list[str] = []
    warnings: list[str] = []

    for entity_id in entity_ids:
        if not isinstance(entity_id, str) or not entity_id.startswith("automation."):
            raise HomeAssistantError(f"Ungültige Automation: {entity_id}")

        if hass.states.get(entity_id) is None:
            # Disabled automations may be absent from the state machine, so
            # the entity registry lookup inside _find_source_raw_config is the
            # authoritative fallback.
            from homeassistant.helpers import entity_registry as er

            if er.async_get(hass).async_get(entity_id) is None:
                raise HomeAssistantError(f"Automation nicht gefunden: {entity_id}")

        raw_config = _find_source_raw_config(hass, entity_id, current)

        use_blueprint = raw_config.get("use_blueprint")
        if not isinstance(use_blueprint, dict):
            raise HomeAssistantError(
                f"{entity_id}: Die Automation verwendet keinen Blueprint."
            )

        source_path = use_blueprint.get("path")
        if source_path == TARGET_BLUEPRINT_PATH:
            skipped.append(f"{entity_id} (bereits neuer Blueprint)")
            continue

        old_inputs = use_blueprint.get("input", {})
        if not isinstance(old_inputs, dict):
            raise HomeAssistantError(
                f"{entity_id}: Die Blueprint-Eingaben konnten nicht gelesen werden."
            )

        if "app_name" not in old_inputs or (
            "entity" not in old_inputs and "entities" not in old_inputs
        ):
            raise HomeAssistantError(
                f"{entity_id}: Sieht nicht wie eine unterstützte AWTRIX-Blueprint-Automation aus."
            )

        source_key, new_config, item_warnings = _build_new_automation(
            hass, entity_id, raw_config, old_inputs, name_prefix, target_awtrix_device
        )

        if skip_existing and _already_migrated(current, source_key):
            skipped.append(f"{entity_id} (bereits migriert)")
            continue

        try:
            await async_validate_config_item(hass, new_config["id"], new_config)
        except Exception as err:  # HA may wrap schema/blueprint errors.
            raise HomeAssistantError(
                f"{entity_id}: Zielautomation ist ungültig: {err}"
            ) from err

        planned.append((entity_id, new_config))
        warnings.extend(f"{entity_id}: {warning}" for warning in item_warnings)

    target_name = target_device.name_by_user or target_device.name or target_awtrix_device

    if not planned:
        return {
            "created": [],
            "skipped": skipped,
            "warnings": warnings,
            "backup": None,
            "dry_run": dry_run,
            "target_device": target_name,
        }

    if dry_run:
        return {
            "created": [config["alias"] for _, config in planned],
            "skipped": skipped,
            "warnings": warnings,
            "backup": None,
            "dry_run": True,
            "target_device": target_name,
        }

    backup_path = await hass.async_add_executor_job(
        _create_backup, automations_path, hass.config.config_dir
    )

    updated = list(current)
    updated.extend(config for _, config in planned)
    await hass.async_add_executor_job(_write_automations_file, automations_path, updated)

    await hass.services.async_call(automation.DOMAIN, SERVICE_RELOAD, blocking=True)

    if disable_originals:
        originals = [entity_id for entity_id, _ in planned]
        if originals:
            await hass.services.async_call(
                automation.DOMAIN,
                SERVICE_TURN_OFF,
                {ATTR_ENTITY_ID: originals},
                blocking=True,
            )

    _LOGGER.info(
        "Migrated %d AWTRIX automation(s) to %s",
        len(planned),
        TARGET_BLUEPRINT_PATH,
    )

    return {
        "created": [config["alias"] for _, config in planned],
        "skipped": skipped,
        "warnings": warnings,
        "backup": backup_path,
        "dry_run": False,
        "target_device": target_name,
    }


async def async_notify_result(hass: HomeAssistant, result: dict[str, Any]) -> None:
    """Show a concise persistent notification after migration."""
    created = result.get("created", [])
    skipped = result.get("skipped", [])
    warnings = result.get("warnings", [])
    dry_run = bool(result.get("dry_run"))
    backup = result.get("backup")
    target_device = result.get("target_device")

    lines = [
        f"{'Prüfung' if dry_run else 'Migration'} abgeschlossen.",
        f"Neue Automationen: {len(created)}",
        f"Übersprungen: {len(skipped)}",
    ]
    if target_device:
        lines.append(f"Ziel-AWTRIX: {target_device}")
    if created:
        lines.append("\nErstellt/geplant:\n- " + "\n- ".join(created))
    if skipped:
        lines.append("\nÜbersprungen:\n- " + "\n- ".join(skipped))
    if warnings:
        lines.append("\nHinweise:\n- " + "\n- ".join(warnings))
    if backup:
        lines.append(f"\nBackup: {backup}")

    await hass.services.async_call(
        "persistent_notification",
        "create",
        {
            "title": "AWTRIX Blueprint Migrator",
            "message": "\n".join(lines),
            "notification_id": "awtrix_blueprint_migrator_last_result",
        },
        blocking=False,
    )
