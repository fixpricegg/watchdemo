"""Bounded stream reads plus actual PostgreSQL upload cleanup and metadata checks."""
import io
import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app import UPLOAD_CHUNK_BYTES, copy_demo, create_app
from tests import test_storage


class UploadLimitUnitTests(unittest.TestCase):
    def test_reads_are_bounded_and_do_not_depend_on_content_length(self):
        calls = []
        class Stream(io.BytesIO):
            def read(self, size=-1):
                self_test.assertGreater(size, 0)
                self_test.assertLessEqual(size, UPLOAD_CHUNK_BYTES)
                calls.append(size)
                return super().read(size)
        self_test = self
        payload = b"x" * (UPLOAD_CHUNK_BYTES + 17)
        destination = io.BytesIO()
        copy_demo(Stream(payload), destination, len(payload))
        self.assertEqual(destination.getvalue(), payload)
        self.assertGreater(len(calls), 2)

    def test_stops_at_one_overflow_byte_without_reading_rest(self):
        source = io.BytesIO(b"x" * 100)
        destination = io.BytesIO()
        with self.assertRaises(HTTPException) as raised:
            copy_demo(source, destination, 16)
        self.assertEqual(raised.exception.status_code, 413)
        self.assertEqual(source.tell(), 17)
        self.assertEqual(destination.getvalue(), b"")

    def test_invalid_config_fails_closed(self):
        for value in ["0", "-1", "invalid", "1.5"]:
            with self.subTest(value=value), patch.dict(os.environ, {"WATCHDEMO_MAX_DEMO_BYTES": value}):
                with self.assertRaisesRegex(RuntimeError, "WATCHDEMO_MAX_DEMO_BYTES"):
                    create_app()

    def test_config_is_read_by_app_factory(self):
        with patch.dict(os.environ, {"WATCHDEMO_MAX_DEMO_BYTES": "42"}):
            self.assertEqual(create_app().state.max_upload_bytes, 42)


@unittest.skipUnless(os.getenv("WATCHDEMO_TEST_DATABASE_URL"), "Explicit test PostgreSQL URL required")
class UploadLimitPostgreSQLTests(unittest.TestCase):
    setUp = test_storage.PostgreSQLStorageTests.setUp
    tearDown = test_storage.PostgreSQLStorageTests.tearDown
    upload = test_storage.PostgreSQLStorageTests.upload

    def test_over_limit_deletes_partial_input_without_creating_match(self):
        limit = UPLOAD_CHUNK_BYTES + 17
        self.client.app.state.max_upload_bytes = limit
        existing = self.directory / "existing.dem"
        existing.write_bytes(b"preserve")
        with patch("app.DemoParser") as parser, patch.object(self.repo, "create_match", wraps=self.repo.create_match) as save:
            response = self.client.post("/demo/upload", files={"file": ("oversized.dem", b"x" * (limit + 1))})
        self.assertEqual(response.status_code, 413, response.text)
        self.assertIn(str(limit), response.json()["detail"])
        parser.assert_not_called()
        save.assert_not_called()
        self.assertEqual(list(self.directory.iterdir()), [existing])
        self.assertEqual(existing.read_bytes(), b"preserve")
        with self.repo.connect() as conn:
            self.assertEqual(conn.execute("SELECT count(*) AS n FROM matches").fetchone()["n"], 0)

    def test_exact_limit_saves_complete_input_and_owned_metadata(self):
        payload = b"x" * 16
        self.client.app.state.max_upload_bytes = len(payload)
        uploaded = self.upload(content=payload)
        self.assertEqual((self.directory / uploaded["filename"]).read_bytes(), payload)
        match = self.repo.get_match(uploaded["match_id"], self.user["id"])
        self.assertEqual(str(match["owner_id"]), self.user["id"])

    def test_below_limit_upload_succeeds(self):
        self.client.app.state.max_upload_bytes = 16
        uploaded = self.upload(content=b"x" * 15)
        self.assertEqual((self.directory / uploaded["filename"]).stat().st_size, 15)
        self.assertEqual(len(self.client.get("/matches").json()["matches"]), 1)
