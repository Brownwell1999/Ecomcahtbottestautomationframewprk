"""Baseline comparison: did this run get better or worse than the version we accepted before?

A fixed threshold only says "this score is acceptable". It cannot see a drop from 0.95 to 0.72 (both pass).
This script compares the last pytest run with a stored baseline, metric by metric.

Flow:  pytest run -> reports/run_scores.json (average score per metric + what was tested)
       -> compare with baseline/baseline.json -> better / same / worse per metric
       -> exit code 0 (no regression) or 1 (a metric dropped by more than the allowed amount)

Two commands:
  python -m baseline.compare_with_baseline            compare the last run with the baseline
  python -m baseline.compare_with_baseline --accept   make the last run the new baseline (for the metrics it ran)

The baseline is stored PER METRIC, because a normal run only covers some tests (judge calls are limited).
Each baseline metric remembers what it was measured with: prompt version, ShopBot's models, judge model,
dataset version. Scores are only comparable when the judge model and the dataset version are the same.

Uses no LLM: it only reads two files.
"""

import argparse
import json
import os
import sys

from framework.utils.config import PROJECT_ROOT, THRESHOLDS

# RUN_SCORES_FILE: in the CI pipeline each quality gate has its own score file (see tests/conftest.py)
RUN_FILE = PROJECT_ROOT / "reports" / os.getenv("RUN_SCORES_FILE", "run_scores.json")
BASELINE_FILE = PROJECT_ROOT / "baseline" / "baseline.json"
MAX_DROP = THRESHOLDS["baseline"]["max_score_drop"]


def compare(run, baseline, max_drop):
    """Compare each metric of the run with its baseline. Returns one row per metric of the run:
    {"metric", "baseline", "current", "change", "verdict", "notes"}.
    verdict: "regression" (dropped by more than max_drop), "improved" (rose by more than max_drop),
             "same" (within the noise), "new" (no baseline for this metric yet)."""
    rows = []
    for name, current in run["metrics"].items():
        row = {"metric": name, "baseline": None, "current": current["average_score"],
               "change": None, "verdict": "new", "notes": []}
        old = baseline.get(name)
        if old is not None:
            row["baseline"] = old["average_score"]
            row["change"] = round(current["average_score"] - old["average_score"], 4)
            if row["change"] < -max_drop:
                row["verdict"] = "regression"
            elif row["change"] > max_drop:
                row["verdict"] = "improved"
            else:
                row["verdict"] = "same"

            # What changed between the two runs: the reason for a difference, or a warning
            for label, new_value in run["labels"].items():
                old_value = old["labels"].get(label)
                if old_value != new_value:
                    row["notes"].append(f"{label}: {old_value} -> {new_value}")
        rows.append(row)
    return rows


def not_comparable(row):
    """A different judge or dataset means the two scores were not measured the same way."""
    return any(note.startswith(("judge_model", "dataset_version")) for note in row["notes"])


def accept(run, baseline):
    """Make this run the baseline for every metric it measured. Other metrics keep their old baseline."""
    for name, current in run["metrics"].items():
        baseline[name] = {**current, "labels": run["labels"], "accepted_from_run_at": run["run_at"]}
    return baseline


def main():
    parser = argparse.ArgumentParser(description="Compare the last pytest run with the stored baseline.")
    parser.add_argument("--accept", action="store_true", help="make the last run the new baseline")
    args = parser.parse_args()

    if not RUN_FILE.exists():
        print(f"No reports/{RUN_FILE.name} found: run some evaluation tests with pytest first.")
        return 2
    run = json.loads(RUN_FILE.read_text(encoding="utf-8"))
    baseline = json.loads(BASELINE_FILE.read_text(encoding="utf-8")) if BASELINE_FILE.exists() else {}

    labels = run["labels"]
    print(f"Last run: {run['run_at']}")
    print(f"  prompt {labels['prompt_version']} | ShopBot models {labels['shopbot_models']} | "
          f"judge {labels['judge_model']} | dataset {labels['dataset_version']}")

    if args.accept:
        BASELINE_FILE.write_text(json.dumps(accept(run, baseline), indent=2), encoding="utf-8")
        print(f"\nAccepted {len(run['metrics'])} metrics as the new baseline: {', '.join(run['metrics'])}")
        print(f"Saved to {BASELINE_FILE} (commit this file so the baseline is shared and has a history).")
        return 0

    rows = compare(run, baseline, MAX_DROP)
    print(f"\nA change of more than {MAX_DROP} counts; smaller changes are run-to-run noise.\n")
    for row in rows:
        if row["verdict"] == "new":
            print(f"  {row['metric']}: {row['current']} (no baseline yet)")
            continue
        print(f"  {row['metric']}: baseline {row['baseline']} -> now {row['current']} "
              f"(change {row['change']:+}) = {row['verdict'].upper()}")
        if baseline[row["metric"]].get("provisional"):
            print("      NOTE: this baseline is an estimate, not a measured run. Replace it with --accept after a good run.")
        for note in row["notes"]:
            print(f"      changed since the baseline: {note}")
        if not_comparable(row):
            print("      WARNING: different judge or dataset, so these two scores are not directly comparable")

    regressions = [row["metric"] for row in rows if row["verdict"] == "regression"]
    if regressions:
        print(f"\nREGRESSION in: {', '.join(regressions)}")
        return 1
    if all(row["verdict"] == "new" for row in rows):
        print("\nNothing to compare yet. Accept this run as the baseline with:  "
              "python -m baseline.compare_with_baseline --accept")
        return 0
    print("\nNo regression.")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
