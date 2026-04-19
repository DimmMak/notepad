"""Tests for .notepad — roundtrip, parser, tag validation, CLI dispatch."""

import datetime as dt
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

HERE = os.path.abspath(os.path.dirname(__file__))
ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
sys.path.insert(0, ROOT)

from scripts.lib import note_io  # noqa: E402
from scripts import notepad as cli  # noqa: E402


class TestFormatAndParse(unittest.TestCase):
    def test_roundtrip_no_tags(self):
        when = dt.datetime(2026, 4, 19, 17, 45).astimezone()
        line = note_io.format_entry("hello world", [], now=when)
        parsed = note_io.parse_entry(line)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["text"], "hello world")
        self.assertEqual(parsed["tags"], [])

    def test_roundtrip_with_tags(self):
        when = dt.datetime(2026, 4, 19, 17, 45).astimezone()
        line = note_io.format_entry("pizza idea", ["food", "ideas"], now=when)
        parsed = note_io.parse_entry(line)
        self.assertEqual(parsed["tags"], ["food", "ideas"])

    def test_strip_hash_prefix(self):
        when = dt.datetime(2026, 4, 19, 17, 45).astimezone()
        line = note_io.format_entry("x", ["#food"], now=when)
        parsed = note_io.parse_entry(line)
        self.assertEqual(parsed["tags"], ["food"])

    def test_newlines_escaped(self):
        when = dt.datetime(2026, 4, 19, 17, 45).astimezone()
        line = note_io.format_entry("line1\nline2", [], now=when)
        self.assertNotIn("\n", line)
        self.assertIn("line1\\nline2", line)

    def test_tag_dedup_preserves_order(self):
        when = dt.datetime(2026, 4, 19, 17, 45).astimezone()
        line = note_io.format_entry("x", ["food", "FOOD", "food", "ideas"], now=when)
        parsed = note_io.parse_entry(line)
        self.assertEqual(parsed["tags"], ["food", "ideas"])

    def test_malformed_returns_none(self):
        self.assertIsNone(note_io.parse_entry("not a bullet"))
        self.assertIsNone(note_io.parse_entry(""))
        self.assertIsNone(note_io.parse_entry(None))

    def test_unicode_text(self):
        when = dt.datetime(2026, 4, 19, 17, 45).astimezone()
        line = note_io.format_entry("café ✨ idea", ["food"], now=when)
        parsed = note_io.parse_entry(line)
        self.assertEqual(parsed["text"], "café ✨ idea")


class TestTagNormalization(unittest.TestCase):
    def test_uppercase_lowercased(self):
        self.assertEqual(note_io.normalize_tag("FOOD"), "food")

    def test_hash_stripped(self):
        self.assertEqual(note_io.normalize_tag("#food"), "food")

    def test_spaces_rejected(self):
        self.assertIsNone(note_io.normalize_tag("two words"))

    def test_hyphens_ok(self):
        self.assertEqual(note_io.normalize_tag("side-project"), "side-project")

    def test_empty_rejected(self):
        self.assertIsNone(note_io.normalize_tag(""))
        self.assertIsNone(note_io.normalize_tag(None))

    def test_max_length(self):
        self.assertEqual(note_io.normalize_tag("a" * 30), "a" * 30)
        self.assertIsNone(note_io.normalize_tag("a" * 31))


class TestAppendRoundtrip(unittest.TestCase):
    def test_append_and_read(self):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False)
        tmp.close()
        try:
            note_io.append_entry("first", ["alpha"], log_path=tmp.name)
            note_io.append_entry("second", ["beta"], log_path=tmp.name)
            entries = list(note_io.iter_entries(tmp.name))
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[0]["text"], "first")
            self.assertEqual(entries[1]["tags"], ["beta"])
        finally:
            os.remove(tmp.name)

    def test_malformed_line_skipped(self):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False)
        tmp.close()
        try:
            with open(tmp.name, "w") as f:
                when = dt.datetime(2026, 4, 19, 17, 45).astimezone()
                f.write(note_io.format_entry("valid one", [], now=when) + "\n")
                f.write("GARBAGE LINE\n")
                f.write(note_io.format_entry("valid two", [], now=when) + "\n")
            entries = list(note_io.iter_entries(tmp.name))
            self.assertEqual(len(entries), 2)
        finally:
            os.remove(tmp.name)


class TestPathSafety(unittest.TestCase):
    def test_inside_root(self):
        self.assertTrue(note_io.is_safe_path("/tmp/a/b/c.md", "/tmp/a"))

    def test_outside_root(self):
        self.assertFalse(note_io.is_safe_path("/etc/passwd", "/tmp/a"))

    def test_traversal_attempt(self):
        self.assertFalse(note_io.is_safe_path("/tmp/a/../../etc/passwd", "/tmp/a"))


class TestCLIDispatch(unittest.TestCase):
    """Smoke-test the CLI dispatcher using a temp log."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False)
        self.tmp.close()
        self._orig_log = cli.LOG_PATH
        cli.LOG_PATH = self.tmp.name
        # Seed with two entries
        when = dt.datetime(2026, 4, 19, 17, 45).astimezone()
        note_io.append_entry("seeded one", ["seed"], log_path=self.tmp.name, now=when)
        note_io.append_entry("seeded two", ["seed", "food"], log_path=self.tmp.name, now=when)

    def tearDown(self):
        cli.LOG_PATH = self._orig_log
        os.remove(self.tmp.name)

    def _run(self, argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli.run(argv)
        return rc, buf.getvalue()

    def test_no_args_shows_recent(self):
        rc, out = self._run([])
        self.assertEqual(rc, 0)
        self.assertIn("seeded one", out)
        self.assertIn("seeded two", out)

    def test_add_subcommand(self):
        rc, out = self._run(["add", "new thing", "#proj"])
        self.assertEqual(rc, 0)
        self.assertIn("Added", out)
        entries = list(note_io.iter_entries(self.tmp.name))
        self.assertEqual(entries[-1]["text"], "new thing")
        self.assertEqual(entries[-1]["tags"], ["proj"])

    def test_free_text_no_subcommand(self):
        rc, out = self._run(["pizza", "idea", "#food"])
        self.assertEqual(rc, 0)
        entries = list(note_io.iter_entries(self.tmp.name))
        self.assertEqual(entries[-1]["text"], "pizza idea")

    def test_tag_filter(self):
        rc, out = self._run(["tag", "food"])
        self.assertEqual(rc, 0)
        self.assertIn("seeded two", out)
        self.assertNotIn("seeded one", out)

    def test_search(self):
        rc, out = self._run(["search", "two"])
        self.assertEqual(rc, 0)
        self.assertIn("seeded two", out)
        self.assertNotIn("seeded one", out)

    def test_stats(self):
        rc, out = self._run(["stats"])
        self.assertEqual(rc, 0)
        self.assertIn("Total entries", out)

    def test_tags_listing(self):
        rc, out = self._run(["tags"])
        self.assertEqual(rc, 0)
        self.assertIn("#seed", out)
        self.assertIn("#food", out)


if __name__ == "__main__":
    unittest.main()
