"""Shared pytest setup. pytest loads this file automatically before the tests."""

import sys

import pytest
from pytest_metadata.plugin import metadata_key

from framework.utils.config import DATASET_VERSION

# ShopBot's replies can contain emoji and special characters. On Windows, printing them fails with
# UnicodeEncodeError when the output goes to a file or a CI log, so print as UTF-8.
# sys.__stdout__ is the real terminal stream: with --capture=tee-sys (pytest.ini) pytest replaces
# sys.stdout with its own capture, but still copies every print to the real one.
for stream in (sys.stdout, sys.__stdout__, sys.stderr, sys.__stderr__):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")


# ---------- Golden dataset version (test_data/dataset_version.yaml) in every report ----------
# Two runs can only be compared fairly when they used the same version of the goldens.

def pytest_report_header(config):
    """First lines of the terminal output."""
    return f"golden dataset version: {DATASET_VERSION}"


@pytest.hookimpl(trylast=True)
def pytest_configure(config):
    """The "Environment" table at the top of reports/report.html."""
    config.stash[metadata_key]["Golden dataset version"] = DATASET_VERSION


@pytest.fixture(scope="session", autouse=True)
def dataset_version_in_junit(record_testsuite_property):
    """A property in reports/junit.xml, so CI can show it too."""
    record_testsuite_property("golden_dataset_version", DATASET_VERSION)
