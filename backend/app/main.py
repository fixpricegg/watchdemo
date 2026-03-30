from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .analysis import analyze_demo_file

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT / "frontend"

app = FastAPI(title="WatchDemo MVP", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/analyze")
async def analyze_demo(file: UploadFile = File(...)) -> dict:
    if not file.filename.lower().endswith(".dem"):
        raise HTTPException(status_code=400, detail="Загрузите файл формата .dem")

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Файл пустой")

    result = analyze_demo_file(file.filename, payload)

    return {
        "file": file.filename,
        "summary": {
            "map": result.map_name,
            "rounds": result.rounds,
            "impact_score": result.impact_score,
        },
        "stats": {
            "kills": result.kills,
            "deaths": result.deaths,
            "assists": result.assists,
            "headshot_percent": result.headshot_percent,
            "adr": result.adr,
            "utility_damage": result.utility_damage,
            "opening_duel_success_percent": result.opening_duel_success_percent,
            "clutch_success_percent": result.clutch_success_percent,
        },
        "mistakes": result.mistakes,
        "recommendations": result.recommendations,
    }


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
