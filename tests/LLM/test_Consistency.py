"""Consistency test for ShopBot with DeepEval GEval.

Consistency = ask the SAME question twice -> does ShopBot give the SAME FACTS both times?
Wording may change (LLMs are non-deterministic), facts must not.
No golden answer: the first answer is the reference for the second.

Flow:  question -> answer 1 -> same question again -> answer 2
       -> judge compares the facts of answer 2 with answer 1 -> PASS / FAIL

Run:  pytest tests/LLM/test_Consistency.py -v -s
Needs: ShopBot running locally (http://localhost:5173) and ANTHROPIC_API_KEY in .env (judge LLM).
"""

import pytest
from deepeval.test_case import LLMTestCase

from framework.assertions.evaluation_assertions import assert_metric_passes
from framework.clients.shopbot_client import send_message
from framework.metrics.llm_metrics import consistency_metric


@pytest.mark.evaluation
def test_consistency_express_shipping():
    # One question with clear facts (days + price)
    question = "How long does express shipping take and what does it cost?"
    metric = consistency_metric()

    # Ask ShopBot the SAME question twice. Each call starts a new conversation (no conversation id),
    # so the second answer can't copy the first from chat history: two independent answers to compare.
    first_answer = send_message(question)["message"]["content"]
    second_answer = send_message(question)["message"]["content"]
    print(f"\nQuestion: {question}\nAnswer 1: {first_answer}\nAnswer 2: {second_answer}")

    # Answer 1 is the reference (expected), answer 2 is checked against it (actual)
    test_case = LLMTestCase(input=question, actual_output=second_answer, expected_output=first_answer)

    # The judge scores how consistent the two answers are (0 to 1)
    assert_metric_passes(metric, test_case)

    # Consistent is not the same as correct: if ShopBot gave the same WRONG fact twice, this test still
    # passes. That is why Consistency is paired with a Correctness test (is it right, and right every time?).
