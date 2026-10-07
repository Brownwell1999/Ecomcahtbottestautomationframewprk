"""Judge calibration: check the judge LLM against verdicts given by a person.

Every evaluation test trusts the judge. But the judge is an LLM too and can be wrong: too strict
(fails a good answer) or too lenient (passes a bad one). This script measures how often the judge
agrees with a human, per metric.

Flow:  labelled examples (a person said "pass" or "fail" for each answer)
       -> run the SAME metric functions the tests use on each example -> the judge's verdict
       -> compare the two verdicts -> agreement per metric + the list of disagreements
       -> exit code 0 (agreement is high enough) or 1 (a metric is below its minimum)

Run it when the judge model changes, when a metric's instructions change, or when you change a threshold.

Run:  python -m judge_calibration.run_calibration
Needs: ANTHROPIC_API_KEY in .env. Labels: test_data/calibration/judge_labels.json.
Cost: one metric evaluation per labelled example (a few judge calls each). ShopBot is not needed.
"""

import json
import sys
from datetime import datetime, timezone

from deepeval.test_case import LLMTestCase

from framework.metrics.chatbot_metrics import answer_relevancy_metric
from framework.metrics.rag_metrics import faithfulness_metric
from framework.metrics.security_metrics import pii_leakage_metric
from framework.utils.config import ANTHROPIC_API_KEY, JUDGE_MODEL, PROJECT_ROOT, THRESHOLDS, load_test_data

MIN_AGREEMENT = THRESHOLDS["calibration"]["min_agreement"]
REPORT_FILE = PROJECT_ROOT / "reports" / "judge_calibration.json"

# The metrics that can be calibrated: the name used in the labels file -> the function that builds the metric
METRICS = {
    "answer_relevancy": answer_relevancy_metric,
    "faithfulness": faithfulness_metric,
    "pii_leakage": pii_leakage_metric,
}


def judge_example(example):
    """Run the judge on one labelled example. Returns the example plus the judge's verdict, score and reason."""
    result = {"id": example["id"], "metric": example["metric"], "human_verdict": example["human_verdict"],
              "judge_verdict": None, "score": None, "reason": None, "error": None}
    metric = METRICS[example["metric"]]()
    test_case = LLMTestCase(input=example["input"], actual_output=example["actual_output"],
                            retrieval_context=example.get("retrieval_context"))
    try:
        metric.measure(test_case)
        result["score"] = metric.score
        result["judge_verdict"] = "pass" if metric.is_successful() else "fail"
        result["reason"] = metric.reason
    except Exception as problem:  # a judge error (rate limit, timeout) is not a verdict
        result["error"] = str(problem)
    return result


def agreement_per_metric(results):
    """Per metric: how often the judge agreed with the human, and in which direction it disagreed.
    too_strict  = human said pass, judge said fail (a false alarm)
    too_lenient = human said fail, judge said pass (a missed defect: the dangerous kind)"""
    summary = {}
    for result in results:
        if result["error"] is not None:
            continue  # errors are reported but don't count as agreement or disagreement
        entry = summary.setdefault(result["metric"], {"compared": 0, "agree": 0, "too_strict": 0, "too_lenient": 0})
        entry["compared"] += 1
        if result["judge_verdict"] == result["human_verdict"]:
            entry["agree"] += 1
        elif result["human_verdict"] == "pass":
            entry["too_strict"] += 1
        else:
            entry["too_lenient"] += 1
    for entry in summary.values():
        entry["agreement"] = entry["agree"] / entry["compared"]
    return summary


def main():
    if not ANTHROPIC_API_KEY:
        print("Set ANTHROPIC_API_KEY in .env to run the judge calibration.")
        return 2

    examples = load_test_data("calibration/judge_labels.json")
    drafts = sum(1 for example in examples if not example.get("confirmed_by_human"))
    print(f"Judge: {JUDGE_MODEL}. Labelled examples: {len(examples)}.")
    if drafts:
        print(f"WARNING: {drafts} labels are drafts that no person has confirmed yet "
              f'(set "confirmed_by_human": true after checking each one).')

    # 1. The judge gives its verdict on every labelled example
    results = []
    for example in examples:
        result = judge_example(example)
        results.append(result)
        if result["error"] is not None:
            print(f"  {result['id']}: ERROR {result['error'][:100]}")
        else:
            same = "agree" if result["judge_verdict"] == result["human_verdict"] else "DISAGREE"
            print(f"  {result['id']}: human {result['human_verdict']}, judge {result['judge_verdict']} "
                  f"(score {result['score']}) -> {same}")

    # 2. Agreement per metric
    summary = agreement_per_metric(results)
    print("\nAgreement with the human labels:")
    for name, entry in summary.items():
        print(f"  {name}: {entry['agree']} of {entry['compared']} = {entry['agreement']:.2f} "
              f"(too strict: {entry['too_strict']}, too lenient: {entry['too_lenient']})")

    # 3. The disagreements, with the judge's reason: this is what to read and act on
    disagreements = [r for r in results if r["error"] is None and r["judge_verdict"] != r["human_verdict"]]
    if disagreements:
        print("\nDisagreements:")
        for result in disagreements:
            print(f"  {result['id']} ({result['metric']}): human {result['human_verdict']}, "
                  f"judge {result['judge_verdict']}. Judge's reason: {result['reason']}")

    # 4. Save the report (with the judge model, so calibrations of different judges can be compared)
    REPORT_FILE.parent.mkdir(exist_ok=True)
    report = {"run_at": datetime.now(timezone.utc).isoformat(), "judge_model": JUDGE_MODEL,
              "unconfirmed_labels": drafts, "min_agreement": MIN_AGREEMENT,
              "agreement": summary, "results": results}
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport saved to {REPORT_FILE}")

    # 5. The gate: a failing exit code when the judge agrees too rarely on any metric
    low = [name for name, entry in summary.items() if entry["agreement"] < MIN_AGREEMENT]
    if low:
        print(f"\nCALIBRATION FAILED: agreement is below {MIN_AGREEMENT} for: {', '.join(low)}")
        return 1
    print(f"\nCalibration passed: every metric agrees with the human labels at least {MIN_AGREEMENT:.0%} of the time.")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
