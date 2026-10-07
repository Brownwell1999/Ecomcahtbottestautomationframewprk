"""Shared pass/fail check for every DeepEval metric test."""

# Every score measured in this pytest run: {"metric", "score", "passed"}.
# tests/conftest.py saves them to reports/run_scores.json at the end of the run,
# and baseline/compare_with_baseline.py compares that file with the stored baseline.
RECORDED_SCORES = []


def assert_metric_passes(metric, test_case):
    """Score the test case with the metric, print the score and the judge's reason,
    and fail the test if the score is below the metric's threshold.

    Works for single-turn test cases (LLMTestCase) and conversations (ConversationalTestCase)."""
    __tracebackhide__ = True  # on failure, pytest points at the line in the test, not at this helper

    # 1. The judge scores the test case (this is where the judge LLM is called)
    metric.measure(test_case)

    # 2. Show the result. metric.__name__ is DeepEval's readable name, e.g. "Answer Relevancy"
    print(f"\n{metric.__name__} score: {metric.score} (threshold {metric.threshold})")
    print(f"Reason: {metric.reason}")

    # 3. Remember the score for the baseline comparison (before the assert, so failures are recorded too)
    RECORDED_SCORES.append({"metric": metric.__name__, "score": metric.score, "passed": bool(metric.is_successful())})

    # 4. PASS when the score is at or above the threshold
    assert metric.is_successful(), f"{metric.__name__} {metric.score} < {metric.threshold}: {metric.reason}"
