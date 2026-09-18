# SpeedSpeechCutter

SpeedSpeechCutter beschleunigt den Zuschnitt einzelner Redebeiträge aus einer durchgehenden Veranstaltungsaufzeichnung. Die Originalaufnahme bleibt unverändert; automatisch erkannte Schnittpunkte werden als Vorschläge angezeigt und vom Bediener geprüft.

## Version 0.3.0

### Bereits umgesetzt

- vorhandene Videoaufnahmen aus `recordings/` einlesen
- Videodauer und technische Metadaten mit ffprobe bestimmen
- Videovorschau im Browser
- manuelle Start-/Endmarken
- automatische Schnittvorschläge aus der Audiospur
- kurze Pausen innerhalb einer Rede zusammenführen
- Mindestlänge für einen Redebeitrag
- konfigurierbarer Vor-/Nachlauf
- automatische Vorschläge per Klick in den manuellen Schnitt übernehmen
- SQLite-Speicherung der bestätigten Schnittmarken
- framegenauer FFmpeg-Export als MP4
- Originalaufnahme wird nicht verändert

## Automatische Analyse

Die erste automatische Stufe verwendet FFmpegs `silencedetect`. Aus längeren Audioaktivitätsblöcken werden mögliche Redebeiträge gebildet.

Standardwerte:

- Stille-Schwelle: **-35 dB**
- minimale Stille: **1,2 s**
- Pausen bis **12 s** innerhalb eines Beitrags zusammenführen
- Mindestlänge eines Vorschlags: **20 s**
- Vor-/Nachlauf: **2 s**

Diese Werte lassen sich in der Weboberfläche anpassen.

Wichtig: In 0.2.0 wird Audioaktivität erkannt, noch keine semantische Rede. Musik, längerer Applaus oder andere laute Programmpunkte können deshalb ebenfalls in einem Vorschlag liegen. Die Vorschläge werden nicht automatisch veröffentlicht oder exportiert; der Bediener übernimmt und korrigiert sie.

## Architektur

- Python 3.11+
- FastAPI
- FFmpeg / ffprobe
- SQLite
- HTML/JavaScript-Oberfläche

## Installation (Debian 12/13)

```bash
sudo apt update
sudo apt install -y python3 python3-venv ffmpeg

git clone https://github.com/Markus4771/SpeedSpeedCutter.git
cd SpeedSpeedCutter

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

mkdir -p data recordings exports
uvicorn app.main:app --host 0.0.0.0 --port 8102
```

Danach:

```
http://SERVER-IP:8102
```

## Arbeitsablauf

1. Durchgehende Aufnahme nach `recordings/` kopieren.
2. Aufnahme in der Weboberfläche auswählen.
3. **Aufnahme analysieren** starten.
4. Gefundene Vorschläge prüfen.
5. Einen Vorschlag in den Schnitt übernehmen.
6. Start/Ende bei Bedarf am Video korrigieren.
7. Schnittmarke speichern.
8. Fertige Rede exportieren.
9. MP4 liegt unter `exports/`.

## API

- `GET /health`
- `GET /api/recordings`
- `GET /api/recordings/{filename}/info`
- `POST /api/analyze`
- `GET /api/cuts`
- `POST /api/cuts`
- `DELETE /api/cuts/{id}`
- `POST /api/cuts/{id}/export`

## Roadmap

### 0.1.x
Manuelle Schnittmarken + FFmpeg-Export. Erledigt.

### 0.2.x
Automatische Audioanalyse und Schnittvorschläge. Erledigt.

### 0.3.x
Whisper-Transkription mit Silero-VAD und sprachbasierten Schnittvorschlägen. Aktueller Stand.

### 0.4.x
Sprecherwechsel / Rednererkennung sowie automatische Zuordnung von Redebeiträgen.

### 0.5.x
Direkte Blackmagic-Capture-Unterstützung, Live-Ringpuffer und Analyse während der laufenden Aufnahme.

## Redaktioneller Workflow

Automatisch erkannte Schnittpunkte sind ausschließlich Vorschläge. Die Auswahl, Korrektur und Freigabe eines Redebeitrags erfolgt durch den Bediener.


## Neu in 0.3.0

Zusätzlich zur schnellen FFmpeg-Audioanalyse gibt es jetzt **Whisper + VAD**:

- `faster-whisper` für deutsche Transkription
- integrierter Silero-VAD-Filter zur Erkennung tatsächlicher Sprache
- sprachbasierte Segmente statt nur Lautstärkeaktivität
- Transkript wird direkt beim Schnittvorschlag angezeigt
- Modellgröße derzeit standardmäßig `small`
- CPU-Betrieb mit `int8`
- `POST /api/analyze/whisper`

Beim ersten Whisper-Lauf wird das Modell geladen. Dafür ist Internetzugriff auf dem Server erforderlich; anschließend kann das Modell aus dem lokalen Cache verwendet werden.

Auch Whisper/VAD kann Applaus, Zwischenrufe oder schwierige Hall-Situationen nicht perfekt einordnen. Schnittpunkte bleiben deshalb redaktionelle Vorschläge.
