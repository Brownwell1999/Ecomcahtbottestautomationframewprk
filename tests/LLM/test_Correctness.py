"""Correctness test for ShopBot with DeepEval GEval.

Correctness = does ShopBot's answer state the SAME FACTS as the correct (expected) answer?
DeepEval has no built-in Correctness metric, so we build one with GEval.

Flow:  question -> ShopBot answer -> compare with expected answer (judge LLM) -> PASS / FAIL

Run:  pytest tests/LLM/test_Correctness.py -v -s
Needs: ShopBot running locally (http://localhost:5173) and ANTHROPIC_API_KEY in .env (judge LLM).
"""

import pytest
from deepeval.test_case import LLMTestCase

from framework.assertions.evaluation_assertions import assert_metric_passes
from framework.clients.shopbot_client import send_message
from framework.metrics.llm_metrics import correctness_steps_metric


@pytest.mark.evaluation
def test_correctness_headphone_warranty():
    # Question + the correct answer (from ShopBot's warranty_policy.md)
    question = "What warranty do headphones have?"
    expected_answer = "Headphones have a 1-year manufacturer warranty from the delivery date."
    metric = correctness_steps_metric()

    # Get ShopBot's actual answer
    actual_answer = send_message(question)["message"]["content"]
    print(f"\nQuestion: {question}\nExpected: {expected_answer}\nActual:   {actual_answer}")

    # Put all three into a test case: this is what the judge compares
    test_case = LLMTestCase(input=question, actual_output=actual_answer, expected_output=expected_answer)

    # The judge scores the answer (0 to 1) by following the evaluation steps in the metric
    assert_metric_passes(metric, test_case)
