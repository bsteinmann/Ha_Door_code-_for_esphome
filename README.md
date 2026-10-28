# Door Code Manager 2.2.0 – NFC

Türcodes für ESPHome-Keypad + Shelly-Türöffner, verwaltet über ein Seitenmenü-Panel **„Türcodes“** (nur Administratoren).

## Installation (HACS)
1. HACS → ⋮ → *Benutzerdefinierte Repositories* → URL dieses Repos, Kategorie *Integration*.
2. *Door Code Manager* herunterladen, Home Assistant **neu starten**.
   (Manuell: Ordner `custom_components/doorcode_manager` nach `/config/custom_components/` kopieren.)
3. Einstellungen → Geräte & Dienste → Integration hinzufügen → *Door Code Manager*:
   Keypad-Sensor (ESPHome-Text-Sensor), Türöffner (switch/button/lock), optional Notify-Dienst.
4. Im Seitenmenü **Türcodes** öffnen (ggf. Browser-Cache leeren / Strg+F5).
5. Alte Keypad-Automationen in `automation.yaml` deaktivieren, sonst öffnet die Tür doppelt.

## NFC-Tags
Jede Person kann einen PIN **und/oder** mehrere NFC-Tags haben. Im Panel: *Neue Person* → **Tag anlernen** →
Tag innerhalb von 30 s an den Leser halten (oder mit der Companion-App scannen). Der angelernte Tag öffnet in dieser Zeit
die Tür nicht. Voraussetzung: Dein Leser meldet Scans an Home Assistant (Event `tag_scanned`), z. B. ESPHome PN532/RC522:

```yaml
pn532_i2c:          # oder rc522_spi, je nach Hardware
  on_tag:
    - homeassistant.tag_scanned: !lambda 'return x;'
```
Optional: In den Integrations-Optionen kannst du die Leser (Geräte) festlegen, deren Tags akzeptiert werden.
Sonst öffnet auch ein Scan mit einer Companion-App, sofern der Tag einer Person gehört.

## Aktionen
Pro Person (PIN oder NFC) lässt sich zusätzlich zur Türöffnung – oder statt ihr, wenn „Tür öffnen“ aus ist –
eine Liste von Entitäten auslösen: Skripte (bekommen `person`, `code_id`, `method`), Szenen, Automationen
(Bedingungen werden übersprungen), Buttons, Schalter/Lichter/Input-Booleans (einschalten), Schlösser (entsperren),
Rollläden/Tore (öffnen). Wer feinere Logik will, nutzt das Event `doorcode_manager_code_used` in einer eigenen Automation.
Achtung: Ein Code kann damit mehr als eine Tür steuern – vergib solche Codes mit Bedacht.

## Benachrichtigungen
Pro Person wählst du die Empfänger aus einer Liste aller Geräte mit Companion-App (mit Personenname, falls zuordenbar).
Ohne Auswahl gelten die Standard-Empfänger aus den Integrations-Optionen (jederzeit änderbar; ältere Einstellung aus der Einrichtung bleibt als Rückfall bestehen).

## Panel
Codes anlegen/bearbeiten/löschen, Zufallscode, Einmalcode (24 h gültig, Schnellanlage), „Gültig ab/bis“,
Aktiv-Schalter, Code anzeigen/verbergen, Live-Status (Bereit / Gesperrt) und Zugriffsverlauf.

## ESPHome (dein Keypad mit `PIN` + `code received`)
Dein `key_collector` passt unverändert. In der Integration wählst du:
- **Keypad-Sensor:** `sensor.<gerät>_pin`
- **Auslöser:** `binary_sensor.<gerät>_code_received`

Der Auslöser ist wichtig: Er pulst bei jeder Eingabe, so funktioniert auch derselbe Code zweimal hintereinander.
Ohne Auslöser reagiert die Integration nur auf Änderungen des Sensors.

Zwei Dinge in deinem Snippet:
- Beim Einfügen ist `platform: template` im `binary_sensor` zerhackt (`templat` / `e`) – im Original prüfen.
- Ein Zahlen-Sensor verliert **führende Nullen** (`0123` kommt als `123` an). Die Integration gleicht das aus
  (`0123` und `123` gelten als derselbe Code und können nicht parallel angelegt werden). Sauberer: zusätzlich
  einen `text_sensor` mit `x` füllen und den als Keypad-Sensor wählen.

## Services (für Automationen)
`doorcode_manager.add_code` (name, code, one_time, notify, valid_from, expires_at),
`delete_code`, `enable_code`, `disable_code` (je `code_id`, die 8-stellige ID steht auf der Code-Karte).

## Events
`doorcode_manager_code_used` (code_id, name, use_count, method = pin|nfc), `..._invalid_code`, `..._lockout_started`,
`..._code_added`, `..._code_deleted`.

## Sicherheit
- Codes liegen **im Klartext** in `/config/.storage/doorcode_manager.codes` (nötig, damit das Panel sie anzeigen kann).
  Wer Zugriff auf `/config` hat oder HA-Administrator ist, kann sie lesen. Backups entsprechend schützen.
- Fehlversuche lösen eine Sperre aus (Optionen: Anzahl, Dauer); falsche Eingaben werden ohne Code protokolliert.
- Nicht kompatibel zu Version 1: Codes aus der ersten Fassung müssen neu angelegt werden.
