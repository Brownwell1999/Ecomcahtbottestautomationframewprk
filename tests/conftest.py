"""Shared pytest setup. pytest loads this file automatically before the tests."""

import json
import os
import sys
from datetime import datetime, timezone

import pytest
from pytest_metadata.plugin import metadata_key

from framework.assertions.evaluation_assertions import RECORDED_SCORES
from framework.clients import shopbot_client
from framework.utils.config import DATASET_VERSION, JUDGE_MODEL, PROJECT_ROOT

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


# ---------- Save this run's scores for the baseline comparison (baseline/compare_with_baseline.py) ----------

def pytest_sessionfinish(session):
    """After the last test: write the average score per metric to reports/run_scores.json,
    labelled with what was tested (prompt version, ShopBot's models, judge model, dataset version)."""
    if not RECORDED_SCORES:
        return  # this run measured no metric (for example only smoke tests): nothing to save

    # Group the recorded scores by metric
    metrics = {}
    for record in RECORDED_SCORES:
        if record["score"] is None:
            continue
        entry = metrics.setdefault(record["metric"], {"cases": 0, "score_total": 0.0, "passed": 0})
        entry["cases"] += 1
        entry["score_total"] += record["score"]
        entry["passed"] += 1 if record["passed"] else 0

    run = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "labels": {
            "prompt_version": shopbot_client.SEEN["prompt_version"],
            "shopbot_models": sorted(shopbot_client.SEEN["models"]),
            "judge_model": JUDGE_MODEL,
            "dataset_version": DATASET_VERSION,
        },
        "metrics": {name: {"cases": entry["cases"],
                           "average_score": round(entry["score_total"] / entry["cases"], 4),
                           "pass_rate": round(entry["passed"] / entry["cases"], 4)}
                    for name, entry in metrics.items()},
    }
    # RUN_SCORES_FILE: the CI pipeline gives each quality gate its own score file, so one gate's run
    # does not overwrite another's (azure-pipelines.yml). Locally it stays run_scores.json.
    report_file = PROJECT_ROOT / "reports" / os.getenv("RUN_SCORES_FILE", "run_scores.json")
    report_file.parent.mkdir(exist_ok=True)
    report_file.write_text(json.dumps(run, indent=2), encoding="utf-8")
