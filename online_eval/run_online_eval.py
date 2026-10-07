"""Online evaluation: score a sample of ShopBot's REAL conversation turns with the same metrics as the tests.

The tests in tests/ are OFFLINE evaluation: we send our own questions before a release.
This job is ONLINE evaluation: it looks at conversations that already happened.

Flow:  LangSmith traces of real turns -> take a random sample -> build DeepEval test cases
       -> score with the SAME metric functions the tests use -> write each score back onto its trace
       -> save a report -> compare the pass rates with the gate in thresholds.yaml
       -> exit code 0 (all good) or 1 (a pass rate is below its gate = the alert)

Real traffic has no golden answer, so only metrics that need just the question, the reply and the
retrieved chunks are used: Answer Relevancy, Toxicity, PII Leakage, and for turns that retrieved chunks
also Faithfulness and Contextual Relevancy.

This is a plain script, not a pytest test. ShopBot does NOT need to be running: the job only needs
LangSmith (the traces) and the judge LLM.

Run:  python -m online_eval.run_online_eval
Needs: LANGSMITH_API_KEY and ANTHROPIC_API_KEY in .env. Settings: the `online` section of thresholds.yaml.
"""

import json
import random
import sys
from datetime import datetime, timezone

from deepeval.test_case import LLMTestCase

from framework.clients.langsmith_client import recent_turns, save_score
from framework.metrics.chatbot_metrics import answer_relevancy_metric
from framework.metrics.rag_metrics import contextual_relevancy_metric, faithfulness_metric
from framework.metrics.security_metrics import pii_leakage_metric, toxicity_metric
from framework.utils.config import ANTHROPIC_API_KEY, LANGSMITH_API_KEY, PROJECT_ROOT, THRESHOLDS

SETTINGS = THRESHOLDS["online"]
REPORT_FILE = PROJECT_ROOT / "reports" / "online_eval.json"


def metrics_for(turn):
    """The metrics that can judge this turn. The two RAG metrics need retrieved chunks."""
    metrics = {
        "answer_relevancy": answer_relevancy_metric(),
        "toxicity": toxicity_metric(),
        "pii_leakage": pii_leakage_metric(),
    }
    if turn["retrieval_context"]:
        metrics["faithfulness"] = faithfulness_metric()
        metrics["contextual_relevancy"] = contextual_relevancy_metric()
    return metrics


def score_turn(turn):
    """Score one real turn with every metric that fits it. Returns one result dict per metric."""
    # An empty reply cannot be judged, and the user saw nothing: count it as a failed answer
    if turn["answer"].strip() == "":
        return [{"run_id": turn["run_id"], "question": turn["question"], "answer": turn["answer"],
                 "metric": "answer_relevancy", "score": 0.0, "passed": False, "reason": "ShopBot returned an empty reply", "error": None}]

    test_case = LLMTestCase(input=turn["question"], actual_output=turn["answer"],
                            retrieval_context=turn["retrieval_context"] or None)
    results = []
    for name, metric in metrics_for(turn).items():
        result = {"run_id": turn["run_id"], "question": turn["question"], "answer": turn["answer"],
                  "metric": name, "score": None, "passed": None, "reason": None, "error": None}
        try:
            metric.measure(test_case)
            result["score"] = metric.score
            result["passed"] = bool(metric.is_successful())
            result["reason"] = metric.reason
        except Exception as problem:  # a judge error (rate limit, timeout) is not a quality failure
            result["error"] = str(problem)
        results.append(result)
    return results


def pass_rates(results):
    """Per metric: how many turns were scored, how many passed, and the pass rate (passed / scored)."""
    rates = {}
    for result in results:
        if result["error"] is not None:
            continue  # errors are reported but don't count for or against the bot
        entry = rates.setdefault(result["metric"], {"scored": 0, "passed": 0})
        entry["scored"] += 1
        if result["passed"]:
            entry["passed"] += 1
    for entry in rates.values():
        entry["rate"] = entry["passed"] / entry["scored"]
    return rates


def gate_failures(rates, min_pass_rate):
    """The metrics whose pass rate is below its minimum, as readable messages. Empty list = gate passed."""
    failures = []
    for name, entry in rates.items():
        minimum = min_pass_rate.get(name)
        if minimum is not None and entry["rate"] < minimum:
            failures.append(f"{name}: pass rate {entry['rate']:.2f} is below the minimum {minimum} "
                            f"({entry['passed']} of {entry['scored']} turns passed)")
    return failures


def main():
    if not LANGSMITH_API_KEY or not ANTHROPIC_API_KEY:
        print("Set LANGSMITH_API_KEY and ANTHROPIC_API_KEY in .env to run the online evaluation.")
        return 2

    # 1. Read the recent real turns and take a random sample
    turns = recent_turns(hours=SETTINGS["lookback_hours"])
    if not turns:
        print(f"No ShopBot turns found in the last {SETTINGS['lookback_hours']} hours: nothing to score.")
        return 0
    sample = random.sample(turns, min(SETTINGS["sample_size"], len(turns)))
    print(f"Found {len(turns)} recent turns, scoring a sample of {len(sample)}.")

    # 2. Score every sampled turn, and write each score back onto its trace in LangSmith
    results = []
    for number, turn in enumerate(sample, start=1):
        print(f"\nTurn {number}: {turn['question']}")
        for result in score_turn(turn):
            results.append(result)
            if result["error"] is not None:
                print(f"  {result['metric']}: ERROR {result['error'][:100]}")
                continue
            print(f"  {result['metric']}: {result['score']} -> {'pass' if result['passed'] else 'FAIL'}")
            if SETTINGS["write_scores_to_langsmith"]:
                save_score(result["run_id"], result["metric"], result["score"], result["reason"])

    # 3. Pass rate per metric, compared with the gate
    rates = pass_rates(results)
    failures = gate_failures(rates, SETTINGS["min_pass_rate"])

    print("\nPass rates:")
    for name, entry in rates.items():
        minimum = SETTINGS["min_pass_rate"].get(name)
        print(f"  {name}: {entry['passed']} of {entry['scored']} passed = {entry['rate']:.2f} (minimum {minimum})")

    # 4. Save the report
    REPORT_FILE.parent.mkdir(exist_ok=True)
    report = {"run_at": datetime.now(timezone.utc).isoformat(), "turns_found": len(turns),
              "turns_scored": len(sample), "pass_rates": rates, "gate_failures": failures, "results": results}
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport saved to {REPORT_FILE}")

    # 5. The alert: a failing exit code when a pass rate is below its gate
    if failures:
        print("\nALERT: quality gate failed")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("\nQuality gate passed.")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # ShopBot's replies can contain emoji
    sys.exit(main())
