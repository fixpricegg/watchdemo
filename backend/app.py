from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
from uuid import UUID, uuid4

from demoparser2 import DemoParser
from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator
import psycopg

from analyzer_service import analyze_demo
from storage.repository import Repository, json_snapshot
from auth import router as auth_router, csrf, current_user
from fastapi.exceptions import RequestValidationError
from report_export import export_report


logger = logging.getLogger(__name__)
UPLOAD_CHUNK_BYTES = 1024 * 1024


def copy_demo(source, destination, max_bytes):
    """Bounded reads, including one lookahead byte at the exact size limit."""
    total = 0
    while chunk := source.read(min(UPLOAD_CHUNK_BYTES, max_bytes - total + 1)):
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(413, f"Размер demo превышает лимит {max_bytes} байт")
        destination.write(chunk)


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


def protect_write(request: Request):
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        csrf(request)


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
    application = FastAPI(title="WatchDemo API", lifespan=lifespan, dependencies=[Depends(protect_write)])
    try:
        max_upload_bytes = int(os.getenv("WATCHDEMO_MAX_DEMO_BYTES", str(1024 ** 3)))
        if max_upload_bytes <= 0:
            raise ValueError()
    except ValueError:
        raise RuntimeError("WATCHDEMO_MAX_DEMO_BYTES must be a positive integer") from None
    application.state.max_upload_bytes = max_upload_bytes
    application.state.origins = [v.strip() for v in os.getenv("WATCHDEMO_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if v.strip()]
    application.include_router(auth_router)

    @application.middleware("http")
    async def private_responses(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @application.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        return JSONResponse(status_code=422, content={"detail": "Проверьте данные (пароль: 12–128 символов)"})
    application.add_middleware(
        CORSMiddleware,
        allow_origins=application.state.origins,
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
    def upload_demo(request: Request, file: UploadFile = File(...), user=Depends(current_user)):
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
                copy_demo(file.file, buffer, request.app.state.max_upload_bytes)
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
            request.app.state.repository.create_match(match_id, filename, players, user["user_id"])
        except BaseException:
            if created:
                destination.unlink(missing_ok=True)
            raise
        finally:
            file.file.close()
        return {"status": "uploaded", "match_id": match_id, "filename": destination.name,
                "original_filename": filename, "players": players}

    @application.post("/demo/analyze")
    def analyze_uploaded_demo(body: AnalyzeRequest, request: Request, user=Depends(current_user)):
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
        match = repo.get_match(match_id, user["user_id"])
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
    def list_matches(request: Request, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), user=Depends(current_user)):
        return {"matches": request.app.state.repository.list_matches(limit, offset, user["user_id"])}

    @application.get("/matches/{match_id}")
    def get_match(match_id: UUID, request: Request, user=Depends(current_user)):
        match = request.app.state.repository.get_match(match_id, user["user_id"])
        if match is None:
            raise HTTPException(404, "Матч не найден")
        return match

    @application.get("/reports")
    def list_reports(request: Request, match_id: UUID | None = None,
                     limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), user=Depends(current_user)):
        return {"reports": request.app.state.repository.list_reports(limit, offset, match_id, user["user_id"])}

    @application.get("/reports/{report_id}")
    def get_report(report_id: UUID, request: Request, user=Depends(current_user)):
        report = request.app.state.repository.get_report(report_id, user["user_id"])
        if report is None:
            raise HTTPException(404, "Отчёт не найден")
        return report

    @application.get("/reports/{report_id}/export")
    def download_report(report_id: UUID, request: Request, user=Depends(current_user)):
        report = request.app.state.repository.get_report(report_id, user["user_id"])
        if report is None:
            raise HTTPException(404, "Отчёт не найден")
        if report["status"] != "completed":
            raise HTTPException(409, "Экспорт доступен после успешного завершения анализа")
        return JSONResponse(export_report(report), headers={
            "Content-Disposition": f'attachment; filename="watchdemo-{report_id}.json"',
            "X-Content-Type-Options": "nosniff",
        })

    return application


app = create_app()
