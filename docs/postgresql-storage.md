# PostgreSQL match and report storage

This implements the saved-match/report requirement in `final_application.md`.
The analyzer, detectors, Match Library, Geometry Layer and their output contract
are unchanged. Persistence wraps the existing `analyze_demo()` result.

## Start a fresh development database

Use a new database/role for this branch. No existing uploads, generated reports,
or database records are imported automatically. PostgreSQL 17.6 was used for QA.

From `backend/`, with PostgreSQL available and the virtual environment active:

```powershell
python -m pip install -r requirements.txt
$env:WATCHDEMO_DATABASE_URL = 'postgresql://watchdemo:your-password@127.0.0.1:5432/watchdemo'
$env:WATCHDEMO_UPLOAD_DIR = 'C:\watchdemo-dev\uploads'
python manage_storage.py migrate
python manage_storage.py check
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

The database and login must already exist. The migration role needs permission
to create the `watchdemo` schema and its tables. Store real credentials outside
Git. `.env.example` documents variables; the API does not load `.env` files.
Without `WATCHDEMO_UPLOAD_DIR`, new uploads use `backend/uploads`, independent
of the shell working directory. Relative configured paths follow the shell's
working directory; prefer an absolute path.

From `frontend/`, run `npm ci` and `npm run dev`. Optional `VITE_API_URL` changes
the default API origin (`http://127.0.0.1:8000`). Navigate to **Reports** to open
saved results. The stable browser URL is `/reports/<report-id>`; refreshing it
loads the result from PostgreSQL. A production frontend host must route SPA
paths to `index.html`.

## Schema and lifecycle

- `matches`: UUID, original display filename, player roster and upload time.
- `reports`: UUID, match FK, selected SteamID/name, `processing` / `completed` /
  `failed`, result format version, map, timestamps and a safe failure message.
- `reports.result`: complete JSONB snapshot of `report`, `radar`,
  `timeline_rounds`, `events`, `stats`, and `report_text`. Reading a completed
  report requires neither the input `.dem` nor a parser or analysis rerun.
- `schema_migrations`: applied migration filename and SHA-256 checksum.

Migration checksums normalize Windows/Linux line endings. Migrations are explicit, transactional, serialized with a PostgreSQL advisory
lock, and forward-only. Repeating `migrate` preserves data. Modified applied
migrations or unknown newer versions are rejected. API startup verifies the
schema instead of migrating it automatically. No destructive rollback command
is provided.

Uploads use fresh UUID filenames and exclusive creation, so two inputs called
`match.dem` never overwrite each other. Only the newly created input is removed
when upload validation or metadata persistence fails. Paths supplied by clients
are never used as filesystem destinations or input paths. Existing legacy files
remain untouched and are not exposed via the filename compatibility field.

Analysis is still synchronous. Each request creates a separate report, including
repeat analysis of the same player. The processing row is committed before
analysis; a separate short transaction atomically saves the entire snapshot and
marks it completed. Serialization/write failures cannot return a successful
analysis response. JSON normalization supports the analyzer's numpy values and
integer object keys; non-finite numbers become `null`, consistently in the HTTP
response and saved snapshot.

A session advisory lock identifies each live analysis across workers. Startup
marks interrupted processing rows failed only when it can acquire that report's
lock; it skips analyses still running in another server process. This requires
direct PostgreSQL connections or session pooling, not a transaction-pooling
proxy. Interrupted analysis is not automatically rerun. If the input remains,
the API can create a new report by analyzing the match again.

Input files are temporary artifacts outside the database. They may be removed
after analysis without affecting saved results. This change deliberately does
not remove successful inputs automatically, allowing analysis of another
player; retention scheduling is separate from report persistence. Missing input
returns 410 when a new analysis is requested, while saved reports still open.

## API contract

| Endpoint | Behavior |
| --- | --- |
| `POST /demo/upload` | Multipart `.dem`; returns `match_id`, opaque `filename`, `original_filename`, `players` |
| `POST /demo/analyze` | `{ "match_id": "UUID", "steamid": "string" }`; returns `report_id`, `match_id`, existing `result` envelope |
| `GET /matches?limit=50&offset=0` | Metadata only, newest first, report counts |
| `GET /matches/{match_id}` | Match metadata and roster; 404 if absent |
| `GET /reports?match_id=UUID&limit=50&offset=0` | Optional match filter; report summaries without heavy result snapshots |
| `GET /reports/{report_id}` | Status, metadata, `format_version` and full result for a completed report |
| `GET /health` | Checks database connectivity; storage errors return 503 |

Lists return `{ "matches": [...] }` and `{ "reports": [...] }`. Pagination is
bounded to 1–100 rows with a nonnegative offset. UUID syntax errors return 422;
absent resources return 404. A failed report has `result: null` and a safe error.
Internal database errors/credentials are not included in HTTP responses.

Compatibility: `/demo/analyze` also accepts the exact opaque `filename` returned
by the new upload endpoint. It does not accept arbitrary preexisting file names.
Use `match_id` for new integrations. The analyzer's result fields are preserved;
the frontend's legacy `/match` view remains available for in-memory results.

Accounts and ownership were added in migration 002; see [accounts-ivr.md](accounts-ivr.md).
All application reads now require the owner's session. Old ownerless rows remain
private. JSON export, background jobs and importing loose report files remain separate work.

## Tests

```powershell
python -m pip install -r requirements-test.txt
# Explicit TEST connection to a disposable instance; never inferred from the app URL.
$env:WATCHDEMO_TEST_DATABASE_URL = 'postgresql://watchdemo_test:your-password@127.0.0.1:5432/watchdemo_test'
python -m unittest tests.test_storage -v
python -m unittest discover -s tests -v
```

Each integration test generates a private `watchdemo_test_<uuid>` schema and
drops only that exact schema afterward. Uploads are created in temporary
directories. The parser/analyzer are substituted with synthetic fixtures for
storage/API tests; persistence itself uses real PostgreSQL, not SQLite or an
in-memory fake. One test kills and relaunches an actual Uvicorn subprocess and
compares full HTTP report payloads after input deletion. Other tests cover
cross-worker recovery, transaction constraints, independent reports/players,
pagination/filtering, migration checksums, cleanup, path isolation, numpy JSON
roundtrips and failure behavior. Without the TEST connection the integration
tests are explicitly skipped; six database-free checks still run.

No real demo files or existing application database were used for this work.
