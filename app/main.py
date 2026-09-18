from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent
RECORDINGS_DIR = BASE_DIR / "recordings"
EXPORTS_DIR = BASE_DIR / "exports"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "speedspeechcutter.db"

for directory in (RECORDINGS_DIR, EXPORTS_DIR, DATA_DIR):
    directory.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="SpeedSpeechCutter", version="0.1.0")


def db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with db() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS cuts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                title TEXT NOT NULL,
                start_seconds REAL NOT NULL,
                end_seconds REAL NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


init_db()


class CutCreate(BaseModel):
    filename: str
    title: str = Field(min_length=1, max_length=200)
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)


def safe_recording(filename: str) -> Path:
    candidate = (RECORDINGS_DIR / filename).resolve()
    if candidate.parent != RECORDINGS_DIR.resolve() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="Aufnahme nicht gefunden")
    return candidate


def probe(path: Path) -> dict[str, Any]:
    process = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,format_name:stream=index,codec_type,codec_name,width,height,r_frame_rate",
            "-of",
            "json",
            str(path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        raise HTTPException(status_code=422, detail=process.stderr.strip() or "ffprobe fehlgeschlagen")
    return json.loads(process.stdout)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/recordings")
def recordings() -> list[dict[str, Any]]:
    result = []
    for path in sorted(RECORDINGS_DIR.iterdir()):
        if not path.is_file() or path.name.startswith("."):
            continue
        try:
            info = probe(path)
            duration = float(info.get("format", {}).get("duration") or 0)
        except Exception:
            duration = 0
        result.append({"filename": path.name, "duration": duration, "size": path.stat().st_size})
    return result


@app.get("/api/recordings/{filename}/info")
def recording_info(filename: str) -> dict[str, Any]:
    return probe(safe_recording(filename))


@app.get("/media/{filename}")
def media(filename: str):
    return FileResponse(safe_recording(filename))


@app.get("/api/cuts")
def list_cuts() -> list[dict[str, Any]]:
    with db() as connection:
        rows = connection.execute("SELECT * FROM cuts ORDER BY id DESC").fetchall()
    return [dict(row) for row in rows]


@app.post("/api/cuts")
def create_cut(cut: CutCreate) -> dict[str, Any]:
    source = safe_recording(cut.filename)
    if cut.end_seconds <= cut.start_seconds:
        raise HTTPException(status_code=422, detail="Ende muss nach dem Start liegen")

    info = probe(source)
    duration = float(info.get("format", {}).get("duration") or 0)
    if duration and cut.end_seconds > duration:
        raise HTTPException(status_code=422, detail="Ende liegt hinter dem Aufnahmeende")

    with db() as connection:
        cursor = connection.execute(
            "INSERT INTO cuts(filename,title,start_seconds,end_seconds) VALUES(?,?,?,?)",
            (cut.filename, cut.title, cut.start_seconds, cut.end_seconds),
        )
        cut_id = cursor.lastrowid
        row = connection.execute("SELECT * FROM cuts WHERE id=?", (cut_id,)).fetchone()
    return dict(row)


@app.delete("/api/cuts/{cut_id}")
def delete_cut(cut_id: int) -> dict[str, bool]:
    with db() as connection:
        cursor = connection.execute("DELETE FROM cuts WHERE id=?", (cut_id,))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Schnittmarke nicht gefunden")
    return {"deleted": True}


@app.post("/api/cuts/{cut_id}/export")
def export_cut(cut_id: int) -> dict[str, str]:
    with db() as connection:
        row = connection.execute("SELECT * FROM cuts WHERE id=?", (cut_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Schnittmarke nicht gefunden")

    source = safe_recording(row["filename"])
    safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in row["title"]).strip("_") or f"rede_{cut_id}"
    output = EXPORTS_DIR / f"{cut_id:04d}_{safe_title}.mp4"

    # Re-encode für framegenaue Schnitte; Copy-Modus kommt später als Option hinzu.
    command = [
        "ffmpeg", "-y",
        "-ss", str(row["start_seconds"]),
        "-t", str(row["end_seconds"] - row["start_seconds"]),
        "-i", str(source),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(output),
    ]
    process = subprocess.run(command, check=False, capture_output=True, text=True)
    if process.returncode != 0:
        raise HTTPException(status_code=500, detail=process.stderr[-3000:])

    return {"filename": output.name, "path": str(output)}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SpeedSpeechCutter</title>
<style>
body{font-family:system-ui,sans-serif;margin:0;background:#111827;color:#e5e7eb}
main{max-width:1200px;margin:auto;padding:24px}
h1{margin-bottom:4px}.muted{color:#9ca3af}
.grid{display:grid;grid-template-columns:2fr 1fr;gap:20px}
.card{background:#1f2937;border-radius:12px;padding:18px;margin-top:20px}
video{width:100%;background:#000;border-radius:8px;max-height:62vh}
input,select,button{box-sizing:border-box;width:100%;padding:10px;margin:5px 0 10px;border-radius:7px;border:1px solid #4b5563;background:#111827;color:#fff}
button{cursor:pointer;background:#2563eb;border:0;font-weight:600}
button.secondary{background:#374151}.row{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.cut{border-top:1px solid #374151;padding:12px 0}
.small{font-size:.9rem;color:#9ca3af}
@media(max-width:850px){.grid{grid-template-columns:1fr}}
</style>
</head>
<body><main>
<h1>SpeedSpeechCutter <span class="small">0.1.0</span></h1>
<div class="muted">Redebeiträge aus einer durchgehenden Veranstaltungsaufnahme schneiden.</div>
<div class="grid">
<section class="card">
<select id="recording"></select>
<video id="video" controls></video>
<div class="row">
<button class="secondary" onclick="setStart()">Aktuelle Zeit = START</button>
<button class="secondary" onclick="setEnd()">Aktuelle Zeit = ENDE</button>
</div>
</section>
<section class="card">
<label>Titel der Rede</label><input id="title" placeholder="z. B. Rede 001">
<div class="row">
<div><label>Start (Sek.)</label><input id="start" type="number" step="0.001" value="0"></div>
<div><label>Ende (Sek.)</label><input id="end" type="number" step="0.001" value="0"></div>
</div>
<button onclick="saveCut()">Schnittmarke speichern</button>
<div id="cuts"></div>
</section>
</div>
</main>
<script>
const rec=document.getElementById('recording'), video=document.getElementById('video');
async function loadRecordings(){
 const items=await (await fetch('/api/recordings')).json();
 rec.innerHTML=items.map(x=>`<option value="${x.filename}">${x.filename} (${x.duration.toFixed(1)} s)</option>`).join('');
 if(items.length){selectRecording();}
}
function selectRecording(){if(rec.value) video.src='/media/'+encodeURIComponent(rec.value)}
rec.onchange=selectRecording;
function setStart(){document.getElementById('start').value=video.currentTime.toFixed(3)}
function setEnd(){document.getElementById('end').value=video.currentTime.toFixed(3)}
async function saveCut(){
 const body={filename:rec.value,title:document.getElementById('title').value||'Rede',start_seconds:+document.getElementById('start').value,end_seconds:+document.getElementById('end').value};
 const r=await fetch('/api/cuts',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(body)});
 if(!r.ok){alert(JSON.stringify(await r.json()));return} await loadCuts();
}
async function exportCut(id){
 const r=await fetch('/api/cuts/'+id+'/export',{method:'POST'});
 const data=await r.json(); if(!r.ok){alert(JSON.stringify(data));return}
 alert('Export erstellt: '+data.filename);
}
async function deleteCut(id){await fetch('/api/cuts/'+id,{method:'DELETE'});await loadCuts()}
async function loadCuts(){
 const items=await (await fetch('/api/cuts')).json();
 document.getElementById('cuts').innerHTML=items.map(x=>`<div class="cut"><b>${x.title}</b><div class="small">${x.filename}<br>${x.start_seconds.toFixed(3)} s – ${x.end_seconds.toFixed(3)} s</div><div class="row"><button onclick="exportCut(${x.id})">Exportieren</button><button class="secondary" onclick="deleteCut(${x.id})">Löschen</button></div></div>`).join('');
}
loadRecordings();loadCuts();
</script></body></html>"""
