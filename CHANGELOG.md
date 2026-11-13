# Door Code Manager v2.2.1

## Behoben
- **README:** Die Überschrift nannte noch „2.0“. Die Versionsnummer steht dort nicht mehr; maßgeblich sind `manifest.json` und die Releases.
- **README:** Der Einrichtungsschritt nannte einen Text-Sensor. Beschrieben ist jetzt das Keypad mit Zahlen-Sensor (`PIN`) und optionalem Auslöser „Code empfangen“.

## Hinweise zum Update
Keine Änderung am Verhalten der Integration. In HACS aktualisieren und Home Assistant neu starten.

## Geänderte Dateien
| Datei | Änderung |
|---|---|
| `custom_components/doorcode_manager/manifest.json` | Version 2.2.1 |
| `custom_components/doorcode_manager/const.py` | Version 2.2.1 |
| `README.md` | Überschrift ohne Versionsnummer, Einrichtungsschritt korrigiert |
| `CHANGELOG.md`, `RELEASE_NOTES_v2.2.1.md` | aktualisiert bzw. neu |

Unverändert: alle übrigen Dateien.

---

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

---

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

---

# Door Code Manager v2.0.4

## Neu
- **NFC-Tags pro Person:** Eine Person kann einen PIN und/oder mehrere NFC-Tags haben. Tags lassen sich im Panel per **„Tag anlernen“** erfassen (Tag an den Leser halten oder mit der Companion-App scannen). Optional in den Optionen: nur Tags bestimmter Leser akzeptieren.
- **Aktionen bei Nutzung:** Zusätzlich zur Türöffnung (oder statt ihr) lassen sich Skripte, Szenen, Automationen, Buttons, Schalter, Lichter, Schlösser und Rollläden auslösen. Skripte erhalten `person`, `code_id` und `method` (`pin`/`nfc`). Auswählbar sind nur Entitäten mit einem **Label**, das in den Optionen festgelegt wird.
- **Benachrichtigungen:** Empfänger pro Person aus einer Liste aller Geräte mit Companion-App (mit Personenname, wenn zuordenbar). Der Standard-Empfänger ist jetzt in den Optionen jederzeit änderbar, nicht mehr nur bei der Einrichtung.
- **Neuer Dialog:** Reiter *Zugang*, *Aktionen* und *Benachrichtigung* für Personen und Einmalcodes.
- **Auslöser-Sensor:** Optionaler Binärsensor („code received“), damit derselbe Code mehrmals hintereinander funktioniert.

## Behoben
- PINs mit führenden Nullen (z. B. `0000`, `0123`) wurden bei Zahlen-Sensoren abgelehnt.
- Schlug das Laden der Empfänger- oder Aktionsliste fehl, gingen beim Speichern bereits gewählte Werte verloren.

## Hinweise zum Update
1. In HACS aktualisieren, Home Assistant **neu starten**, Panel mit Strg+F5 neu laden.
2. Bestehende Codes bleiben erhalten (Datenformat abwärtskompatibel).
3. Für Aktionen: Label anlegen, an Entitäten vergeben und in den Integrations-Optionen auswählen (siehe README).
4. Codes liegen weiterhin im Klartext in `/config/.storage/doorcode_manager.codes`. Codes mit Aktionen können mehr als die Tür steuern – bewusst vergeben.
5. Bitte NFC und Aktionen zuerst mit harmlosen Zielen testen.

## Geänderte Dateien
| Datei | Änderung |
|---|---|
| `custom_components/doorcode_manager/manifest.json` | Version 2.0.4, Dokumentations-Link und Codeowner |
| `custom_components/doorcode_manager/const.py` | Version 2.0.4 (Cache-Busting des Panels), neue Optionen/Konstanten |
| `custom_components/doorcode_manager/manager.py` | NFC-Tags, Anlernmodus, Aktionen, Empfängerlisten, Label-Filter, Null-Fix |
| `custom_components/doorcode_manager/api.py` | neue Websocket-Befehle (Tag anlernen, Empfänger, Aktions-Entitäten) |
| `custom_components/doorcode_manager/__init__.py` | Service-Schema (Tags, Aktionen, Tür öffnen) |
| `custom_components/doorcode_manager/config_flow.py` | Optionen: Tag-Leser, Label, Standard-Empfänger, Auslöser-Sensor |
| `custom_components/doorcode_manager/frontend/doorcode-panel.js` | Dialog mit Reitern, NFC, Aktionen, Empfänger |
| `custom_components/doorcode_manager/services.yaml` | neue Felder `tags`, `open_door`, `actions` |
| `custom_components/doorcode_manager/translations/de.json`, `en.json`, `strings.json` | neue Options-Texte |
| `README.md` | Doku zu NFC, Aktionen, Benachrichtigungen, ESPHome |
| `CHANGELOG.md`, `RELEASE_NOTES_v2.0.4.md` | neu |

Unverändert: `sensor.py`, `hacs.json`, `.gitignore`.
