"""Hallucination test for ShopBot with DeepEval HallucinationMetric (built-in).

Hallucination = does the answer CONTRADICT facts we know are true (the context)?
We give the judge the true facts; it checks the answer doesn't invent or change them.

Flow:  question -> ShopBot answer -> compare with known true facts (judge LLM) -> PASS / FAIL

Run:  pytest tests/LLM/test_Hallucination.py -v -s
Needs: ShopBot running locally (http://localhost:5173) and JUDGE_API_KEY in .env (judge LLM).
"""

import pytest
from deepeval.test_case import LLMTestCase

from framework.assertions.evaluation_assertions import assert_metric_passes
from framework.clients.shopbot_client import send_message
from framework.metrics.llm_metrics import hallucination_metric


@pytest.mark.evaluation
def test_hallucination_express_shipping():
    # Question + the TRUE facts (from ShopBot's shipping_policy.md)
    question = "How long does express shipping take and what does it cost?"
    true_facts = ["Express shipping takes 2-3 business days and costs $12.99."]
    metric = hallucination_metric()

    # Get ShopBot's actual answer
    actual_answer = send_message(question)["message"]["content"]
    print(f"\nQuestion: {question}\nTrue facts: {true_facts}\nActual: {actual_answer}")

    # Answer + true facts (context) in one test case
    test_case = LLMTestCase(input=question, actual_output=actual_answer, context=true_facts)

    # Judge scores the answer: 1.0 = agrees with all facts, 0 = contradicts them
    assert_metric_passes(metric, test_case)

    # context vs retrieval_context:
    #   context           = facts YOU know are true (used by HallucinationMetric)
    #   retrieval_context = chunks ShopBot's retriever found (used by FaithfulnessMetric)
    # A faithful answer can still hallucinate if the retrieved chunks were wrong.
