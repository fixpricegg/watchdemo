from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
import shutil
from uuid import UUID, uuid4

from demoparser2 import DemoParser
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator
import psycopg

from analyzer_service import analyze_demo
from storage.repository import Repository, json_snapshot


logger = logging.getLogger(__name__)


class AnalyzeRequest(BaseModel):
    match_id: UUID | None = None
    # Compatibility: filename is now the opaque token returned by /demo/upload.
    filename: str | None = None
    steamid: str = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def require_match(self):
        if self.match_id is None and not self.filename:
            raise ValueError("match_id or upload filename is required")
        return self


def create_app(*, repository=None, upload_dir=None):
    @asynccontextmanager
    async def lifespan(application):
        repo = repository or Repository(os.environ.get("WATCHDEMO_DATABASE_URL"))
        # Migrations are explicit: API startup never creates/rewrites the schema.
        repo.check_schema()
        repo.recover_interrupted()
        application.state.repository = repo
        directory.mkdir(parents=True, exist_ok=True)
        yield

    configured_dir = upload_dir or os.environ.get("WATCHDEMO_UPLOAD_DIR")
    directory = Path(configured_dir) if configured_dir else Path(__file__).with_name("uploads")
    directory = directory.resolve()
    application = FastAPI(title="WatchDemo API", lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
    )

    @application.exception_handler(psycopg.Error)
    async def storage_error(request: Request, exc):
        logger.error("PostgreSQL operation failed (%s)", type(exc).__name__)
        return JSONResponse(status_code=503, content={"detail": "Хранилище временно недоступно"})

    @application.get("/health")
    def health(request: Request):
        with request.app.state.repository.connect() as conn:
            conn.execute("SELECT 1")
        return {"status": "ok"}

    @application.post("/demo/upload")
    def upload_demo(request: Request, file: UploadFile = File(...)):
        filename = (file.filename or "").replace("\\", "/").rsplit("/", 1)[-1]
        if not filename.lower().endswith(".dem") or len(filename) > 255:
            raise HTTPException(400, "Можно загружать только .dem файлы (имя до 255 символов)")
        match_id = uuid4()
        destination = directory / f"{match_id}.dem"
        created = False
        try:
            # Never overwrite another upload, even if its original name matches.
            with destination.open("xb") as buffer:
                created = True
                shutil.copyfileobj(file.file, buffer)
            try:
                player_info = DemoParser(str(destination)).parse_player_info()
                players = [{
                    "name": str(row.name), "steamid": str(row.steamid),
                    "team": {2: "T", 3: "CT"}.get(int(row.team_number), "UNKNOWN"),
                } for row in player_info.itertuples(index=False)]
                if not players:
                    raise ValueError("No players")
            except Exception:
                raise HTTPException(400, "Не удалось прочитать демку или найти игроков") from None
            request.app.state.repository.create_match(match_id, filename, players)
        except BaseException:
            if created:
                destination.unlink(missing_ok=True)
            raise
        finally:
            file.file.close()
        return {"status": "uploaded", "match_id": match_id, "filename": destination.name,
                "original_filename": filename, "players": players}

    @application.post("/demo/analyze")
    def analyze_uploaded_demo(body: AnalyzeRequest, request: Request):
        repo = request.app.state.repository
        match_id = body.match_id
        if match_id is None:
            try:
                # Exact UUID token only; never use a client-supplied filesystem path.
                match_id = UUID(body.filename.removesuffix(".dem"))
                if body.filename != f"{match_id}.dem":
                    raise ValueError()
            except ValueError:
                raise HTTPException(404, "Загруженная демка не найдена") from None
        match = repo.get_match(match_id)
        if match is None:
            raise HTTPException(404, "Матч не найден")
        steamid = body.steamid.strip()
        player = next((p for p in match["players"] if p["steamid"] == steamid), None)
        if player is None:
            raise HTTPException(404, "Игрок с таким SteamID не найден в демке")
        demo_path = directory / f"{match_id}.dem"
        if not demo_path.is_file():
            raise HTTPException(410, "Временная демка недоступна; сохранённые отчёты можно открыть из истории")
        report_id = None
        try:
            with repo.analysis(match_id, steamid, player["name"]) as report_id:
                result = json_snapshot(analyze_demo(str(demo_path), player["name"]))
                repo.complete_report(report_id, result)
        except psycopg.Error:
            raise
        except Exception:
            logger.exception("Demo analysis failed (report %s)", report_id)
            raise HTTPException(500, {"message": "Ошибка анализа демки", "report_id": str(report_id)}) from None
        return {"status": "analyzed", "match_id": match_id, "report_id": report_id,
                "filename": f"{match_id}.dem", "player": player, "result": result}

    @application.get("/matches")
    def list_matches(request: Request, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
        return {"matches": request.app.state.repository.list_matches(limit, offset)}

    @application.get("/matches/{match_id}")
    def get_match(match_id: UUID, request: Request):
        match = request.app.state.repository.get_match(match_id)
        if match is None:
            raise HTTPException(404, "Матч не найден")
        return match

    @application.get("/reports")
    def list_reports(request: Request, match_id: UUID | None = None,
                     limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
        return {"reports": request.app.state.repository.list_reports(limit, offset, match_id)}

    @application.get("/reports/{report_id}")
    def get_report(report_id: UUID, request: Request):
        report = request.app.state.repository.get_report(report_id)
        if report is None:
            raise HTTPException(404, "Отчёт не найден")
        return report

    return application


app = create_app()
