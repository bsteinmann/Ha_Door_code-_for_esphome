# Door Code Manager v2.2.0

## Neu
- **Fehlversuche mit eingegebenem Code:** Im Verlauf steht bei abgelehnten Versuchen jetzt der eingegebene PIN bzw. die Tag-ID, nicht nur „Abgelehnt“.
- **Neuer Reiter „Fehlversuche“:** Tabelle der abgelehnten Eingaben, sortiert nach Häufigkeit – Code/Tag, Art (PIN/NFC), Anzahl der Versuche, Zeitpunkt des letzten Versuchs und ein Hinweis. Der Hinweis zeigt, ob der Code unbekannt ist oder zu einem Eintrag gehört, der gerade nicht nutzbar ist (abgelaufen, deaktiviert, bereits verbraucht, noch nicht gültig). Mit „Zurücksetzen“ lässt sich die Tabelle leeren.
- **Neue Option:** „Falsch eingegebene Codes und unbekannte Tags protokollieren“ (Standard: an). Ist sie aus, wird nichts gespeichert; die Sperre nach Fehlversuchen funktioniert trotzdem.

## Hinweise
1. In HACS aktualisieren, Home Assistant **neu starten**, Panel mit Strg+F5 neu laden. Bestehende Daten bleiben erhalten.
2. Fehlversuche werden erst ab dieser Version aufgezeichnet; frühere sind nicht rekonstruierbar.
3. Es werden maximal 200 verschiedene Codes geführt; bei Überschreitung fallen die seltensten und ältesten heraus.
4. Eingaben während einer Sperre werden nicht ausgewertet und deshalb nicht erfasst.
5. Führende Nullen: Der PIN-Sensor des Keypads ist eine Zahl, daher erscheint ein falsch eingegebenes `0000` als `0` und `0123` als `123`.
6. Datenschutz: Falsch eingegebene Werte liegen im Klartext in `/config/.storage/doorcode_manager.codes`. Ein Tippfehler kann ein echter PIN sein (z. B. eine Ziffer daneben). Das Event `doorcode_manager_invalid_code` enthält bewusst nur den Grund (`reason`), nicht den Code.

## Geänderte Dateien
| Datei | Änderung |
|---|---|
| `custom_components/doorcode_manager/manifest.json` | Version 2.2.0 |
| `custom_components/doorcode_manager/const.py` | Version 2.2.0, neue Konstanten (Option, Obergrenze) |
| `custom_components/doorcode_manager/manager.py` | Erfassung und Auswertung der Fehlversuche, Verlaufseinträge, Speicherung |
| `custom_components/doorcode_manager/api.py` | neuer Befehl „Fehlversuche zurücksetzen“ |
| `custom_components/doorcode_manager/config_flow.py` | neue Option zum Protokollieren |
| `custom_components/doorcode_manager/frontend/doorcode-panel.js` | Reiter „Fehlversuche“ mit Tabelle, Code im Verlauf |
| `custom_components/doorcode_manager/translations/de.json`, `en.json`, `strings.json` | Text der neuen Option |
| `README.md` | Abschnitt „Fehlversuche“ |
| `CHANGELOG.md`, `RELEASE_NOTES_v2.2.0.md` | aktualisiert bzw. neu |

Unverändert: `__init__.py`, `sensor.py`, `services.yaml`, `hacs.json`, `.gitignore`, `RELEASE_NOTES_v2.0.4.md`, `RELEASE_NOTES_v2.1.0.md`.
