# Door Code Manager v2.1.0

## Neu
- **Eigenständige Aktionen:** Zusätzlich zu den Personen gibt es im Panel eine eigene Ansicht **„Aktionen“**. Eine Aktion hat einen eigenen PIN und/oder NFC-Tags, Gültigkeit und Benachrichtigung und löst nur die gewählten Entitäten aus – die Tür bleibt zu. Beispiele: Alarmanlage scharf stellen, Wallbox-Einstellungen für ein Auto anpassen, alle Lichter ausschalten (jeweils als Skript hinterlegt).
- **Zwei Ansichten im Panel:** *Personen* und *Aktionen* mit Zähler; „Neue Person“/„Neue Aktion“ passt sich der Ansicht an. Der Dialog heißt für Aktionen *Auslöser* statt *Zugang* und blendet „Tür öffnen“ aus.
- **Verlauf und Events kennen die Art:** Einträge zeigen „Aktion ausgelöst“; das Event `doorcode_manager_code_used` enthält jetzt `kind` (`person`/`action`).
- **Benachrichtigung für Aktionen:** „<Name> wurde per PIN/NFC-Tag ausgelöst.“
- **Service `add_code`:** neues Feld `kind` (`person`/`action`, Standard `person`).

## Hinweise zum Update
1. In HACS aktualisieren, Home Assistant **neu starten**, Panel mit Strg+F5 neu laden.
2. Bestehende Einträge bleiben erhalten und gelten als *Personen*.
3. Ein PIN oder NFC-Tag gehört genau einem Eintrag – über Personen und Aktionen hinweg.
4. Aktionen nutzen dieselbe Label-Auswahl wie bisher (Integrations-Optionen). Für komplexe Abläufe (Alarmanlage, Wallbox) ein Skript bauen und dieses labeln.
5. Sicherheit: Wer einen Alarm per PIN *entschärft*, macht ihn so erratbar wie den PIN; die Sperre nach Fehlversuchen gilt gemeinsam für alle Eingaben.

## Geänderte Dateien
| Datei | Änderung |
|---|---|
| `custom_components/doorcode_manager/manifest.json` | Version 2.1.0 |
| `custom_components/doorcode_manager/const.py` | Version 2.1.0 (Cache-Busting des Panels) |
| `custom_components/doorcode_manager/manager.py` | Einträge mit `kind`, Validierung, Benachrichtigungstexte, Verlauf/Event |
| `custom_components/doorcode_manager/api.py` | Feld `kind` im Websocket-Schema |
| `custom_components/doorcode_manager/__init__.py` | Service-Schema mit `kind` |
| `custom_components/doorcode_manager/services.yaml` | Feld `kind` |
| `custom_components/doorcode_manager/frontend/doorcode-panel.js` | Ansichten Personen/Aktionen, angepasster Dialog |
| `README.md` | Abschnitt „Eigenständige Aktionen“ |
| `CHANGELOG.md`, `RELEASE_NOTES_v2.1.0.md` | aktualisiert bzw. neu |

Unverändert: `sensor.py`, `config_flow.py`, Übersetzungen, `strings.json`, `hacs.json`, `.gitignore`, `RELEASE_NOTES_v2.0.4.md`.
