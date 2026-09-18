# SpeedSpeechCutter

SpeedSpeechCutter unterstützt den schnellen Zuschnitt einzelner Redebeiträge aus einer durchgehenden Veranstaltungsaufzeichnung.

## Ziel von 0.1.0

- vorhandene Videoaufnahmen einlesen
- Videodauer und technische Metadaten bestimmen
- Schnittmarken (Start/Ende) erfassen
- Schnittmarken in einer Weboberfläche verwalten
- Vorschau per Browser
- Redebeiträge mit FFmpeg als eigene MP4-Dateien exportieren
- Originalaufnahme bleibt unverändert

Die automatische Redenerkennung wird ab 0.2.x ergänzt. Version 0.1.0 bildet zunächst den heutigen manuellen Arbeitsablauf digital und reproduzierbar ab.

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

Danach im Browser öffnen:

```
http://SERVER-IP:8102
```

## Ablauf

1. Videodatei nach `recordings/` kopieren.
2. Aufnahme in der Weboberfläche auswählen.
3. Start- und Endzeit der Rede eingeben.
4. Schnittmarke speichern.
5. Export starten.
6. Fertige Datei liegt unter `exports/`.

## Roadmap

### 0.1.x
Manuelle Schnittmarken + FFmpeg-Export.

### 0.2.x
Automatische Spracherkennung (VAD) und Vorschläge für Anfang/Ende.

### 0.3.x
Whisper-Transkription und automatische Titel.

### 0.4.x
Sprecherwechsel / Rednererkennung.

### 0.5.x
Direkte Blackmagic-Capture-Unterstützung und Live-Ringpuffer.

## Sicherheit / redaktioneller Workflow

Automatisch erkannte Schnittpunkte sind Vorschläge. Die redaktionelle Freigabe bleibt beim Bediener.
