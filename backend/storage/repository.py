"""Short PostgreSQL transactions; complete analysis snapshots stored in JSONB."""

from contextlib import contextmanager
import hashlib
from pathlib import Path
import re
from uuid import uuid4

import orjson
import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


MIGRATIONS = Path(__file__).with_name("migrations")


def migration_checksum(path):
    # Git may check out CRLF on Windows and LF on Linux. Hash canonical SQL text.
    source = path.read_text(encoding="utf-8")
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def json_snapshot(value):
    # Same numpy/non-string-key support as radar's existing JSON exporter.
    # Non-finite floats become JSON null, so the saved and HTTP values agree.
    return orjson.loads(orjson.dumps(
        value, option=orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_NON_STR_KEYS,
    ))


class Repository:
    def __init__(self, database_url, schema="watchdemo"):
        if not database_url:
            raise RuntimeError("Set WATCHDEMO_DATABASE_URL before starting the API")
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", schema):
            raise ValueError("Invalid storage schema")
        self.database_url = database_url
        self.schema = schema

    def connect(self, *, autocommit=False):
        return psycopg.connect(
            self.database_url, row_factory=dict_row, autocommit=autocommit,
            connect_timeout=5,
            options=f"-c search_path={self.schema},pg_catalog -c statement_timeout=15000",
        )

    def migrate(self):
        """Explicit, transactional, serialized, forward-only migrations."""
        with self.connect() as conn:
            conn.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(current_database() || %s, 0))",
                (self.schema + ":migrations",),
            )
            conn.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(self.schema)))
            conn.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY, checksum TEXT NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )""")
            applied = {r["version"]: r["checksum"] for r in conn.execute(
                "SELECT version, checksum FROM schema_migrations"
            )}
            files = sorted(MIGRATIONS.glob("[0-9]*.sql"))
            if set(applied) - {p.name for p in files}:
                raise RuntimeError("Database has migrations newer than this application")
            for path in files:
                checksum = migration_checksum(path)
                if path.name in applied:
                    if applied[path.name] != checksum:
                        raise RuntimeError(f"Migration checksum changed: {path.name}")
                    continue
                conn.execute(path.read_text(encoding="utf-8"))
                conn.execute("INSERT INTO schema_migrations (version, checksum) VALUES (%s, %s)",
                             (path.name, checksum))

    def check_schema(self):
        with self.connect() as conn:
            applied = {r["version"]: r["checksum"] for r in conn.execute(
                "SELECT version, checksum FROM schema_migrations"
            )}
        expected = {p.name: migration_checksum(p)
                    for p in MIGRATIONS.glob("[0-9]*.sql")}
        if applied != expected:
            raise RuntimeError("Storage schema mismatch; run python manage_storage.py migrate")

    def create_match(self, match_id, filename, players):
        with self.connect() as conn:
            conn.execute("INSERT INTO matches (id, original_filename, players) VALUES (%s, %s, %s)",
                         (match_id, filename, Jsonb(players)))

    def get_match(self, match_id):
        with self.connect() as conn:
            return conn.execute("SELECT * FROM matches WHERE id = %s", (match_id,)).fetchone()

    def list_matches(self, limit, offset):
        with self.connect() as conn:
            return conn.execute("""SELECT m.*, (
                SELECT count(*) FROM reports r WHERE r.match_id = m.id
            ) AS report_count FROM matches m
                ORDER BY created_at DESC, id DESC LIMIT %s OFFSET %s""", (limit, offset)).fetchall()

    @contextmanager
    def analysis(self, match_id, steamid, player_name):
        """Session lock survives commits, but PostgreSQL releases it on process death.

        Recovery skips live analyses, including ones running in another worker.
        No transaction stays open during expensive demo analysis.
        """
        report_id = uuid4()
        with self.connect(autocommit=True) as conn:
            conn.execute("SELECT pg_advisory_lock(hashtextextended(%s, 0))", (str(report_id),))
            conn.execute("""INSERT INTO reports (id, match_id, steamid, player_name, status)
                VALUES (%s, %s, %s, %s, 'processing')""",
                         (report_id, match_id, steamid, player_name))
            try:
                yield report_id
            except BaseException:
                conn.execute("""UPDATE reports SET status = 'failed', error = %s, finished_at = now()
                    WHERE id = %s AND status = 'processing'""",
                             ("Не удалось обработать или сохранить результат анализа", report_id))
                raise
            finally:
                conn.execute("SELECT pg_advisory_unlock(hashtextextended(%s, 0))", (str(report_id),))

    def complete_report(self, report_id, result):
        with self.connect() as conn:
            updated = conn.execute("""UPDATE reports SET status = 'completed', result = %s,
                map_name = %s, finished_at = now() WHERE id = %s AND status = 'processing'""",
                                   (Jsonb(result), result.get("report", {}).get("map"), report_id))
            if updated.rowcount != 1:
                raise RuntimeError("Report is no longer processing")

    def recover_interrupted(self):
        with self.connect() as conn:
            report_ids = [r["id"] for r in conn.execute("SELECT id FROM reports WHERE status = 'processing'")]
            for report_id in report_ids:
                locked = conn.execute("SELECT pg_try_advisory_xact_lock(hashtextextended(%s, 0)) AS ok",
                                      (str(report_id),)).fetchone()["ok"]
                if locked:
                    conn.execute("""UPDATE reports SET status = 'failed', error = %s, finished_at = now()
                        WHERE id = %s AND status = 'processing'""",
                                 ("Обработка прервана перезапуском сервера; запустите анализ повторно", report_id))

    def get_report(self, report_id):
        with self.connect() as conn:
            return conn.execute("""SELECT r.*, m.original_filename FROM reports r
                JOIN matches m ON m.id = r.match_id WHERE r.id = %s""", (report_id,)).fetchone()

    def list_reports(self, limit, offset, match_id=None):
        # Never load the heavy replay snapshot for the history screen.
        with self.connect() as conn:
            return conn.execute("""SELECT r.id, r.match_id, r.steamid, r.player_name, r.status,
                r.format_version, r.map_name, r.error, r.created_at, r.finished_at, m.original_filename
                FROM reports r JOIN matches m ON m.id = r.match_id
                WHERE (%s::uuid IS NULL OR r.match_id = %s)
                ORDER BY r.created_at DESC, r.id DESC LIMIT %s OFFSET %s""",
                                (match_id, match_id, limit, offset)).fetchall()
