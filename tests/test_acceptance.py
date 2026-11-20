from contextlib import closing
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import call, patch

from scripts import probe

with patch.dict(sys.modules, {"probe": probe}):
    from scripts import acceptance


class AcceptancePolicyTests(unittest.TestCase):
    def test_quiet_service_journals_are_checked_in_same_window(self):
        with patch.object(acceptance, "journal", return_value="") as journal, patch.object(acceptance, "log"):
            self.assertTrue(acceptance.check_rejected_upstream_forwards("@123.456789"))
        self.assertEqual(journal.call_args_list, [
            call("--since=@123.456789", unit="9router-clean-bridge"),
            call("--since=@123.456789", unit="9router-clean-protocol"),
        ])

    def test_observed_forward_fails_and_both_units_are_checked(self):
        with patch.object(acceptance, "journal", side_effect=["forwarded fixture\n", ""]) as journal:
            with patch.object(acceptance, "log"):
                self.assertFalse(acceptance.check_rejected_upstream_forwards("@123.456789"))
        self.assertEqual(journal.call_count, 2)

    def test_unexpected_unrestricted_active_key_fails_registry(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(acceptance, "log"):
            root = Path(directory)
            db_path = root / "data" / "db" / "data.sqlite"
            db_path.parent.mkdir(parents=True)
            scopes = (
                ("canary", "free/gemini-3.8-flash"),
                ("free-first-windows-cursor", "free/gemini-3.8-flash"),
                ("free-first-windows-codex", "free/gemini-3.8-flash"),
                ("free-first-pilot-lite", "free/gemini-3.5-flash-lite"),
                ("free-first-pilot-31-lite", "free/gemini-3.1-flash-lite"),
                ("free-first-pilot-lite-fallback", "free/gemini-lite-safe-fallback"),
            )
            with closing(sqlite3.connect(db_path)) as conn, conn:
                conn.execute("CREATE TABLE apiKeys (name, accessRestricted, accessAllow, isActive)")
                conn.executemany(
                    "INSERT INTO apiKeys VALUES (?, ?, ?, ?)",
                    [(name, 1, json.dumps([model]), 1) for name, model in scopes],
                )
            self.assertTrue(acceptance.stored_key_policy(root))

            with closing(sqlite3.connect(db_path)) as conn, conn:
                conn.execute("INSERT INTO apiKeys VALUES (?, ?, ?, ?)", ("unexpected-fixture", 0, "[]", 1))
            self.assertFalse(acceptance.stored_key_policy(root))
