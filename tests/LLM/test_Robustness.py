"""Robustness test for ShopBot with DeepEval GEval.

Robustness = if the user asks the SAME question in a MESSY way (typos, slang, shouting, extra words),
does ShopBot still give the CORRECT answer? Every messy question has the same golden answer as the
clean question "What warranty do headphones have?".

Flow:  messy question -> ShopBot answer -> compare with the golden answer (judge LLM) -> PASS / FAIL

Run:  pytest tests/LLM/test_Robustness.py -v -s
Needs: ShopBot running locally (http://localhost:5173) and ANTHROPIC_API_KEY in .env (judge LLM).
"""

import pytest
from deepeval.test_case import LLMTestCase

from framework.assertions.evaluation_assertions import assert_metric_passes
from framework.clients.shopbot_client import send_message
from framework.metrics.llm_metrics import robustness_metric
from framework.utils.config import load_test_data

# The same golden answer for every messy version of the question
EXPECTED_ANSWER = "Headphones have a 1-year manufacturer warranty."

# Typos, slang, shouting, extra words
MESSY_QUESTIONS = load_test_data("llm/robustness.json")


@pytest.mark.evaluation
@pytest.mark.parametrize("question", MESSY_QUESTIONS, ids=lambda q: q[:35])
def test_robustness(question):
    metric = robustness_metric()

    # Ask ShopBot the messy question
    actual_answer = send_message(question)["message"]["content"]
    print(f"\nMessy question: {question}\nActual: {actual_answer}")

    # Question + actual answer + golden answer = what the judge compares
    test_case = LLMTestCase(input=question, actual_output=actual_answer, expected_output=EXPECTED_ANSWER)

    assert_metric_passes(metric, test_case)
