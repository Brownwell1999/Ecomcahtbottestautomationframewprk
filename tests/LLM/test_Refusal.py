"""Refusal tests for ShopBot with DeepEval GEval (3 sides).

Side 1 - MUST REFUSE:     out-of-scope, harmful, other people's data, system prompt, medical advice
Side 2 - MUST NOT REFUSE: valid shopping requests, even when they look off-topic or come from an angry user
Side 3 - REFUSAL QUALITY: when it refuses, it is polite, brief, gives a reason and redirects

There is no built-in refusal metric, so each side is a GEval metric (see framework/metrics/llm_metrics.py).
Each case's expected_output describes the expected BEHAVIOUR (not an exact answer).

Run:  pytest tests/LLM/test_Refusal.py -v -s
Needs: ShopBot running locally (http://localhost:5173) and JUDGE_API_KEY in .env (judge LLM).
"""

import pytest
from deepeval.test_case import LLMTestCase

from framework.assertions.evaluation_assertions import assert_metric_passes
from framework.clients.shopbot_client import send_message
from framework.metrics.llm_metrics import must_help_metric, must_refuse_metric, refusal_quality_metric
from framework.utils.config import load_test_data

DATA = load_test_data("llm/refusal.json")  # {"must_refuse": [...], "must_help": [...], "refusal_quality": [...]}


def check(case, metric):
    """Ask ShopBot the case's question, score the reply with the metric, assert it passed."""
    actual = send_message(case["input"])["message"]["content"]
    print(f"\nQuestion: {case['input']}\nExpected: {case['expected_output']}\nActual:   {actual}")

    # An empty reply is neither a refusal nor help: the user would see nothing
    assert actual.strip() != "", f"ShopBot returned an empty reply for: {case['input']!r}"

    test_case = LLMTestCase(input=case["input"], actual_output=actual, expected_output=case["expected_output"])
    assert_metric_passes(metric, test_case)


# parametrize = run the same test once per case; ids gives each case a readable name in the report
@pytest.mark.evaluation
@pytest.mark.parametrize("case", DATA["must_refuse"], ids=lambda c: c["input"][:35])
def test_side1_must_refuse(case):
    check(case, must_refuse_metric())


@pytest.mark.evaluation
@pytest.mark.parametrize("case", DATA["must_help"], ids=lambda c: c["input"][:35])
def test_side2_must_not_refuse(case):
    check(case, must_help_metric())


@pytest.mark.evaluation
@pytest.mark.parametrize("case", DATA["refusal_quality"], ids=lambda c: c["input"][:35])
def test_side3_refusal_quality(case):
    check(case, refusal_quality_metric())
