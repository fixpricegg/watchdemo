from pathlib import Path
import shutil

from demoparser2 import DemoParser
from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
from analyzer_service import analyze_demo
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="WatchDemo API"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

class AnalyzeRequest(BaseModel):
    filename: str
    steamid: str

@app.get("/health")
def health():
    return {
        "status": "ok"
    }


@app.post("/demo/upload")
async def upload_demo(
    file: UploadFile = File(...)
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Файл не передан"
        )

    if not file.filename.lower().endswith(".dem"):
        raise HTTPException(
            status_code=400,
            detail="Можно загружать только .dem файлы"
        )

    destination = UPLOAD_DIR / file.filename

    with destination.open("wb") as buffer:
        shutil.copyfileobj(
            file.file,
            buffer
        )

    try:
        parser = DemoParser(str(destination))
        player_info = parser.parse_player_info()

        players = []

        for _, row in player_info.iterrows():
            team_number = int(row["team_number"])

            if team_number == 2:
                team = "T"
            elif team_number == 3:
                team = "CT"
            else:
                team = "UNKNOWN"

            players.append({
                "name": str(row["name"]),
                "steamid": str(row["steamid"]),
                "team": team
            })

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Не удалось прочитать демку: {e}"
        )

    return {
        "status": "uploaded",
        "filename": file.filename,
        "players": players
    }

@app.post("/demo/analyze")
def analyze_uploaded_demo(
    request: AnalyzeRequest
):
    filename = request.filename
    steamid = request.steamid

    demo_path = UPLOAD_DIR / filename

    if not demo_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Загруженная демка не найдена"
        )

    try:
        parser = DemoParser(str(demo_path))
        player_info = parser.parse_player_info()

        players_by_steamid = {}

        for row in player_info.itertuples(index=False):
            player_steamid = str(row.steamid)
            players_by_steamid[player_steamid] = str(row.name)

        target_steamid = steamid.strip()

        player_name = players_by_steamid.get(target_steamid)

        if player_name is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "message": "Игрок с таким SteamID не найден в демке",
                    "requested_steamid": target_steamid,
                    "available_steamids": list(players_by_steamid.keys())
                }
            )

        result = analyze_demo(
            str(demo_path),
            player_name
        )

        return {
            "status": "analyzed",
            "filename": filename,
            "player": {
                "name": player_name,
                "steamid": target_steamid
            },
            "result": result
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка анализа демки: {e}"
        )