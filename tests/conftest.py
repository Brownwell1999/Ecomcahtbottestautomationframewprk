"""Shared pytest setup. pytest loads this file automatically before the tests."""

import sys

# ShopBot's replies can contain emoji and special characters. On Windows, printing them fails with
# UnicodeEncodeError when the output goes to a file or a CI log, so print as UTF-8.
# sys.__stdout__ is the real terminal stream: with --capture=tee-sys (pytest.ini) pytest replaces
# sys.stdout with its own capture, but still copies every print to the real one.
for stream in (sys.stdout, sys.__stdout__, sys.stderr, sys.__stderr__):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")
