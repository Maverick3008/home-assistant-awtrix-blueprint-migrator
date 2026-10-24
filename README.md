# AWTRIX Blueprint Migrator v0.1.8

Home Assistant Custom Integration zum Kopieren alter AWTRIX-Blueprint-Automationen (10der/awtrix-simple)
auf den neuen **AWTRIX NG Layout-App (TC002) Extended** Blueprint.

## Eigenschaften

- echte Custom Integration, kein Helper
- Auswahl mehrerer `automation.*` Entitäten in einer Home-Assistant-Aktion
- Original-Automationen bleiben erhalten
- optional Originale nach erfolgreicher Migration ausschalten
- Dry-Run / Prüfung ohne Schreibzugriff
- validiert jede neue Automation vor dem Schreiben
- erstellt vor Änderungen ein Backup von `automations.yaml`
- verhindert auf Wunsch doppelte Migrationen
- installiert den passenden Ziel-Blueprint automatisch

## Installation

Kopiere den Ordner

`custom_components/awtrix_blueprint_migrator`

nach

`/config/custom_components/awtrix_blueprint_migrator`

und starte Home Assistant neu.

Danach unter **Einstellungen → Geräte & Dienste → Integration hinzufügen**
`AWTRIX Blueprint Migrator` hinzufügen.

Der Ziel-Blueprint wird automatisch installiert unter:

`/config/blueprints/automation/awtrix_blueprint_migrator/awtrix_ng_layout_app_extended.yaml`

## Migration verwenden

Unter **Entwicklerwerkzeuge → Aktionen**:

`awtrix_blueprint_migrator.migrate`

aufrufen, bei **Alte Automationen** mehrere alte AWTRIX-Automationen auswählen und unter **Neues AWTRIX-Zielgerät** die neue AWTRIX NG auswählen.

Empfehlung beim ersten Durchlauf:

- `Nur prüfen`: **ein**
- `Originale danach ausschalten`: **aus**
- `Bereits migrierte überspringen`: **ein**

Wenn die Prüfung erfolgreich ist, `Nur prüfen` ausschalten und erneut ausführen.

## Übernommene Alt-Einstellungen

| Alt | Neu |
|---|---|
| `app_name` | `app_name` |
| `app_icon` | `icon` |
| `entity` | `entities: [entity]` |
| `prefix_text` | `prefix_text` |
| `suffix_text` | `suffix_text` |
| `extra_triggers` | `extra_triggers` |
| `pre_actions` | `pre_actions` |
| `additional_conditions` | `additional_conditions` |
| `awtrix_device` | wird **nicht** übernommen; stattdessen wird das ausgewählte neue Zielgerät gesetzt |
| `user_options` | `user_options` |
| `additional_options.value_template` | `value_template` |
| `additional_options.icon_template` | `icon_template` |

Das Ziellayout wird bei alten Ein-Entitäts-Automationen auf `icon_value` gesetzt.

## Backup

Vor einem echten Schreibvorgang wird eine Sicherung unter

`/config/.awtrix_blueprint_migrator_backups/`

erstellt.

## Wichtiger Hinweis zu automations.yaml

Home Assistants UI-/Config-API-Automationen werden in der Standarddatei
`automations.yaml` gespeichert. Diese Datei muss in deiner Home-Assistant-Konfiguration
auch geladen werden. Wenn du ausschließlich `!include_dir_merge_list` für Automationen
verwendest, musst du `automations.yaml` zusätzlich einbinden.


### Neue Option ab v0.1.2

Die Aktion besitzt das Pflichtfeld **Neues AWTRIX-Zielgerät** (`target_awtrix_device`). Alle ausgewählten alten Automationen werden auf dieses Gerät kopiert. Die Quellautomationen bleiben unverändert.

## Version 0.1.3

- Config-Flow robuster gemacht: keine Automation-/Blueprint-Interna mehr beim Paketimport.
- Migration-spezifische Home-Assistant-Imports werden erst beim tatsächlichen Migrieren geladen.
- Ziel-AWTRIX-Geräteauswahl aus v0.1.1 bleibt erhalten.


## Version 0.1.6

- echter sichtbarer Config-Flow mit Formular
- Auswahl des Standard-AWTRIX-NG-Zielgeräts beim Einrichten
- Standard-Präfix für neu erzeugte Automationen im Config-Flow
- Zielgerät und Präfix können in der Migrations-Aktion optional überschrieben werden
- bestehende Quellautomationen werden weiterhin niemals gelöscht


## v0.1.6

- Liest die ursprünglichen Blueprint-Inputs zuverlässig aus `automations.yaml` statt aus der bereits expandierten `raw_config`.
- Fallback auf die von Home Assistant gehaltenen Blueprint-Inputs für Sonderfälle.
- Konkrete Fehler werden als Home-Assistant-Benachrichtigung angezeigt und als `ServiceValidationError` an die UI zurückgegeben.


## v0.1.6

- Entfernt die Abhängigkeit von `homeassistant.components.automation.const.DATA_COMPONENT`.
- Ordnet ausgewählte Automation-Entities über das Home-Assistant Entity Registry ihrer `id` in `automations.yaml` zu.
- Dadurch kompatibler mit Home-Assistant-Versionen, in denen sich Automation-Interna geändert haben.


## v0.1.7

- Der `app_name` wird bereits **während der Migration** AWTRIX-NG-kompatibel normalisiert.
  Beispiel: `Tage bis zur Hochzeit` → `tagebiszurhochzeit`.
- Regeln: Kleinbuchstaben, `ä/ö/ü/ß` → `ae/oe/ue/ss`, Leerzeichen entfernt, nur `a-z`, `0-9`, `_`, `-`, maximal 32 Zeichen.
- Die erzeugte Automation enthält den bereinigten Namen direkt im `use_blueprint.input.app_name`.
- Bereits vorhandene Ziel-Blueprint-Dateien werden beim Start der Integration **nicht mehr überschrieben**. Eigene Blueprint-Anpassungen bleiben dadurch erhalten.
- Der mitgelieferte Blueprint enthält zusätzlich die aktuelle App-Namen-Absicherung, 5-Minuten-Refresh und die String-Ausgabe für numerische Icon-IDs.


## v0.1.8

- Mitgelieferter Blueprint auf den aktuellen Stand gebracht.
- Neues Layout **16×16 Icon + breiter Wert**.
- Das breite Layout verwendet standardmäßig `matrix-chunky8x6`.
- Automatische `_16`-Icon-Nutzung für mit dem AWTRIX NG Icon Scaler erzeugte 16×16-Dateien.
- Automatische `_16`-Nutzung kann pro Automation deaktiviert werden.
- Font-Auswahl für Wert 1, Wert 2, Wert 3 und Titel.
- Numerische Legacy-Icon-IDs werden bei der Migration ausdrücklich als String übernommen.
- App-Namen werden weiterhin bereits bei der Migration normalisiert.
- Vorhandene Ziel-Blueprint-Dateien werden weiterhin nicht ungefragt überschrieben. Bei einer Neuinstallation wird der aktuelle v0.1.8-Blueprint automatisch installiert.
