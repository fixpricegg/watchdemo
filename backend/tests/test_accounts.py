"""Real PostgreSQL and real loopback SMTP; synthetic demo analysis only."""
import os
import re
import socket
import unittest
from uuid import uuid4
from unittest.mock import patch

from aiosmtpd.controller import Controller
from fastapi.testclient import TestClient
import psycopg

from app import create_app
from auth import COOKIE, digest, verify
from tests import test_storage as storage_tests
from tests.test_storage import authenticate


@unittest.skipUnless(os.getenv("WATCHDEMO_TEST_DATABASE_URL"), "Explicit test PostgreSQL URL required")
class AccountTests(unittest.TestCase):
    setUp = storage_tests.PostgreSQLStorageTests.setUp
    tearDown = storage_tests.PostgreSQLStorageTests.tearDown
    upload = storage_tests.PostgreSQLStorageTests.upload
    analyze = storage_tests.PostgreSQLStorageTests.analyze

    def second_client(self):
        client = TestClient(create_app(repository=self.repo, upload_dir=self.directory))
        client.__enter__()
        self.addCleanup(client.__exit__, None, None, None)
        return client

    def test_registration_case_insensitive_unique_argon2_and_session_cookie(self):
        duplicate = self.client.post("/auth/register", json={"email": "STORAGE@example.com", "password": "Another-password-123", "display_name": "Duplicate"})
        self.assertEqual(duplicate.status_code, 409)
        with self.repo.connect() as conn:
            user = conn.execute("SELECT * FROM users").fetchone()
            self.assertTrue(user["password_hash"].startswith("$argon2id$"))
            self.assertTrue(verify(user["password_hash"], "Storage-Password-123"))
            token = self.client.cookies.get(COOKIE)
            self.assertEqual(conn.execute("SELECT user_id FROM sessions WHERE token_hash=%s", (digest(token),)).fetchone()["user_id"], user["id"])
        fresh = self.second_client()
        response = fresh.get("/auth/session")
        cookie = response.headers["set-cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=lax", cookie)
        with patch.dict(os.environ, {"WATCHDEMO_COOKIE_SECURE": "true"}):
            fresh.cookies.clear()
            self.assertIn("Secure", fresh.get("/auth/session").headers["set-cookie"])

    def test_ownership_direct_urls_lists_reanalysis_and_anonymous_access(self):
        analyzed = self.analyze(self.upload())
        other = self.second_client()
        for path in ["/matches", "/reports", f"/reports/{analyzed['report_id']}"]:
            self.assertEqual(other.get(path).status_code, 401)
        authenticate(other, "other@example.com")
        self.assertEqual(other.get("/matches").json()["matches"], [])
        self.assertEqual(other.get("/reports").json()["reports"], [])
        for path in [f"/matches/{analyzed['match_id']}", f"/reports/{analyzed['report_id']}"]:
            self.assertEqual(other.get(path).status_code, 404)
        self.assertEqual(other.post("/demo/analyze", json={"match_id": analyzed["match_id"], "steamid": "76561198000000001"}).status_code, 404)
        self.assertEqual(other.post("/demo/analyze", json={"filename": analyzed["filename"], "steamid": "76561198000000001"}).status_code, 404)

    def test_legacy_unowned_rows_are_not_claimed_or_public(self):
        from pathlib import Path
        import tempfile
        from psycopg import sql
        from storage.repository import Repository, MIGRATIONS
        repo = Repository(self.url, "watchdemo_test_" + uuid4().hex)
        legacy = uuid4()
        try:
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder)
                (path / "001_matches_reports.sql").write_bytes((MIGRATIONS / "001_matches_reports.sql").read_bytes())
                with patch("storage.repository.MIGRATIONS", path):
                    repo.migrate()
            with repo.connect() as conn:
                conn.execute("INSERT INTO matches (id,original_filename,players) VALUES (%s,'legacy.dem','[]')", (legacy,))
            with repo.analysis(legacy, "123", "Legacy") as report_id:
                repo.complete_report(report_id, {"report": {"map": "legacy"}})
            repo.migrate()
            with repo.connect() as conn:
                self.assertIsNone(conn.execute("SELECT owner_id FROM matches WHERE id=%s", (legacy,)).fetchone()["owner_id"])
                self.assertEqual(conn.execute("SELECT result FROM reports WHERE id=%s", (report_id,)).fetchone()["result"], {"report": {"map": "legacy"}})
            with TestClient(create_app(repository=repo, upload_dir=self.directory)) as fresh:
                authenticate(fresh)
                self.assertEqual(fresh.get(f"/matches/{legacy}").status_code, 404)
                self.assertEqual(fresh.get(f"/reports/{report_id}").status_code, 404)
                self.assertEqual(fresh.get("/matches").json()["matches"], [])
                self.assertEqual(fresh.get("/reports").json()["reports"], [])
            with self.assertRaises(psycopg.errors.CheckViolation):
                repo.create_match(uuid4(), "new-without-owner.dem", [])
        finally:
            with repo.connect() as conn:
                conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(repo.schema)))

    def test_logout_revokes_cookie_even_when_replayed(self):
        token = self.client.cookies.get(COOKIE)
        self.assertEqual(self.client.post("/auth/logout").status_code, 200)
        self.client.cookies.set(COOKIE, token)
        self.assertEqual(self.client.get("/reports").status_code, 401)

    def test_profile_and_password_change_revoke_all_sessions(self):
        other = self.second_client()
        authenticate(other)
        self.assertEqual(self.client.patch("/auth/profile", json={"display_name": "Новое имя"}).status_code, 200)
        self.assertEqual(self.client.get("/auth/profile").json()["display_name"], "Новое имя")
        self.assertEqual(self.client.post("/auth/password", json={"old_password": "wrong", "password": "New-password-1234"}).status_code, 400)
        self.assertEqual(self.client.post("/auth/password", json={"old_password": "Storage-Password-123", "password": "New-password-1234"}).status_code, 200)
        self.assertEqual(other.get("/reports").status_code, 401)
        self.assertEqual(self.client.get("/auth/profile").status_code, 401)
        authenticate(self.client, password="New-password-1234")

    def test_csrf_origin_session_rotation_and_cors(self):
        old = self.client.cookies.get(COOKIE)
        self.assertEqual(self.client.post("/auth/logout", headers={"X-CSRF-Token": "bad"}).status_code, 403)
        self.assertEqual(self.client.post("/auth/logout", headers={"Origin": "https://evil.example"}).status_code, 403)
        self.assertEqual(self.client.post("/auth/logout", headers={"Origin": "null"}).status_code, 403)
        authenticate(self.client)
        self.assertNotEqual(old, self.client.cookies.get(COOKIE))
        with self.repo.connect() as conn:
            self.assertIsNone(conn.execute("SELECT * FROM sessions WHERE token_hash=%s", (digest(old),)).fetchone())
        allowed = self.client.options("/auth/login", headers={"Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "x-csrf-token,content-type"})
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed.headers["access-control-allow-credentials"], "true")
        rejected = self.client.options("/auth/login", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
        self.assertNotIn("access-control-allow-origin", rejected.headers)

    def test_missing_csrf_token_and_cross_session_token_cannot_write(self):
        token = self.client.headers.pop("X-CSRF-Token")
        for path, method, payload in [
            ("/auth/logout", "POST", None),
            ("/auth/profile", "PATCH", {"display_name": "Forbidden"}),
            ("/auth/password", "POST", {"old_password": "Storage-Password-123", "password": "Forbidden-password-123"}),
        ]:
            with self.subTest(path=path):
                self.assertEqual(self.client.request(method, path, json=payload).status_code, 403)
        other = self.second_client()
        other_token = other.get("/auth/session").json()["csrf_token"]
        self.assertEqual(self.client.post("/auth/logout", headers={"X-CSRF-Token": other_token}).status_code, 403)
        self.assertEqual(self.client.post("/auth/logout", headers={"X-CSRF-Token": b"\xff"}).status_code, 403)
        self.client.headers["X-CSRF-Token"] = token
        self.assertEqual(self.client.get("/auth/profile").json()["display_name"], "Storage User")

    def test_forbidden_uploads_do_not_parse_or_create_data(self):
        for headers in [{"X-CSRF-Token": ""}, {"Origin": "https://evil.example"}]:
            with self.subTest(headers=headers), patch("app.DemoParser") as parser:
                response = self.client.post("/demo/upload", files={"file": ("private.dem", b"input")}, headers=headers)
                self.assertEqual(response.status_code, 403)
                parser.assert_not_called()
        anonymous = self.second_client()
        anonymous.headers["X-CSRF-Token"] = anonymous.get("/auth/session").json()["csrf_token"]
        self.assertEqual(anonymous.post("/demo/upload", files={"file": ("guest.dem", b"input")}).status_code, 401)
        self.assertEqual(list(self.directory.iterdir()), [])
        self.assertEqual(self.client.get("/matches").json()["matches"], [])

    def test_recovery_real_smtp_one_use_expiry_uniform_response_and_revocation(self):
        messages = []
        class Mailbox:
            async def handle_DATA(self, server, session, envelope):
                from email.parser import BytesParser
                from email.policy import default
                messages.append(BytesParser(policy=default).parsebytes(envelope.content).get_content())
                return "250 OK"
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0)); port = sock.getsockname()[1]
        server = Controller(Mailbox(), hostname="127.0.0.1", port=port)
        server.start()
        try:
            with patch.dict(os.environ, {"WATCHDEMO_SMTP_HOST": "127.0.0.1", "WATCHDEMO_SMTP_PORT": str(port), "WATCHDEMO_SMTP_TLS": "none"}):
                exists = self.client.post("/auth/forgot-password", json={"email": "storage@example.com"})
                absent = self.client.post("/auth/forgot-password", json={"email": "absent@example.com"})
                self.assertEqual(exists.json(), absent.json())
                self.assertEqual(len(messages), 1)
                token = re.search(r"reset-password#([A-Za-z0-9_-]+)", messages[0]).group(1)
                with self.repo.connect() as conn:
                    stored = conn.execute("SELECT token_hash FROM password_resets").fetchone()["token_hash"]
                    self.assertEqual(stored, digest(token))
                old = self.client.cookies.get(COOKIE)
                payload = {"token": token, "password": "Reset-password-1234"}
                self.assertEqual(self.client.post("/auth/reset-password", json=payload).status_code, 200)
                self.client.cookies.set(COOKIE, old)
                self.assertEqual(self.client.get("/reports").status_code, 401)
                self.client.cookies.clear()
                authenticate(self.client, password="Reset-password-1234")
                self.assertEqual(self.client.post("/auth/reset-password", json=payload).status_code, 400)
                self.client.post("/auth/forgot-password", json={"email": "storage@example.com"})
                expired = re.search(r"reset-password#([A-Za-z0-9_-]+)", messages[-1]).group(1)
                with self.repo.connect() as conn:
                    conn.execute("UPDATE password_resets SET expires_at=now()-interval '1 second'")
                self.assertEqual(self.client.post("/auth/reset-password", json={**payload, "token": expired}).status_code, 400)
        finally:
            server.stop()

    def test_expired_session_and_login_failure_are_generic(self):
        with self.repo.connect() as conn:
            conn.execute("UPDATE sessions SET expires_at=now()-interval '1 second'")
        self.assertEqual(self.client.get("/reports").status_code, 401)
        self.client.headers["X-CSRF-Token"] = self.client.get("/auth/session").json()["csrf_token"]
        known = self.client.post("/auth/login", json={"email": "storage@example.com", "password": "Wrong-password-123"})
        unknown = self.client.post("/auth/login", json={"email": "missing@example.com", "password": "Wrong-password-123"})
        self.assertEqual(known.status_code, 401)
        self.assertEqual(known.json(), unknown.json())

    def test_database_errors_and_validation_do_not_expose_secrets(self):
        with patch.object(self.repo, "connect", side_effect=psycopg.OperationalError("password=TOP_SECRET")):
            response = self.client.get("/auth/profile")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("TOP_SECRET", response.text)
        invalid = self.client.post("/auth/register", json={"email": "bad", "password": "SECRET", "display_name": "x"})
        self.assertEqual(invalid.status_code, 422)
        self.assertNotIn("SECRET", invalid.text)

    def test_rate_limit_persists_between_app_instances(self):
        with self.repo.connect() as conn:
            from auth import digest
            conn.execute("INSERT INTO auth_limits VALUES (%s, 20, now()+interval '15 minutes') ON CONFLICT (key) DO UPDATE SET attempts=20", (digest("login:testclient"),))
        response = self.client.post("/auth/login", json={"email": "storage@example.com", "password": "Storage-Password-123"})
        self.assertEqual(response.status_code, 429)


if __name__ == "__main__":
    unittest.main()
