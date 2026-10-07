"""Admits Unknown test for ShopBot with DeepEval GEval.

ShopBot's RAG prompt says: "If the excerpts don't contain the answer, say you don't have that
information and suggest contacting support." These questions are NOT in the knowledge base,
so ShopBot must say it doesn't know - never invent an answer.

Flow:  question not in the knowledge base -> ShopBot answer
       -> GEval "Admits Unknown" (judge LLM) -> PASS / FAIL

Run:  pytest tests/PROMPT/test_Admits_Unknown.py -v -s
Needs: ShopBot running locally (http://localhost:5173) and ANTHROPIC_API_KEY in .env (judge LLM).
"""

import pytest
from deepeval.test_case import LLMTestCase

from framework.assertions.evaluation_assertions import assert_metric_passes
from framework.clients.shopbot_client import send_message
from framework.metrics.prompt_metrics import admits_unknown_metric
from framework.utils.config import load_test_data

# Questions whose answers are NOT in ShopBot's knowledge base
QUESTIONS = load_test_data("prompt/admits_unknown.json")

# The same expected BEHAVIOUR for every question (not an exact answer)
EXPECTED_BEHAVIOUR = "Should say it doesn't have that information (and may suggest contacting support)."


@pytest.mark.evaluation
@pytest.mark.parametrize("question", QUESTIONS, ids=lambda q: q[:35])
def test_admits_unknown(question):
    metric = admits_unknown_metric()

    # Ask ShopBot something it cannot know
    actual_answer = send_message(question)["message"]["content"]
    print(f"\nQuestion: {question}\nActual:   {actual_answer}")

    # An empty reply is not an honest "I don't know": the user would see nothing
    assert actual_answer.strip() != "", f"ShopBot returned an empty reply for: {question!r}"

    # Question + actual answer + expected behaviour = what the judge compares
    test_case = LLMTestCase(input=question, actual_output=actual_answer, expected_output=EXPECTED_BEHAVIOUR)

    # The judge checks ShopBot admitted it doesn't know, with no invented price, number, date or promise
    assert_metric_passes(metric, test_case)
