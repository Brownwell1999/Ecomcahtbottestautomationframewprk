"""Negative multi-turn test for ShopBot with DeepEval.

ShopBot's knowledge base file data/knowledge_base/trade_in_policy.md is WRONG on purpose:
it has pizza text instead of a real trade-in policy. RAG retrieves it for trade-in questions,
so ShopBot's replies go off-topic and the metric score should drop below the threshold.

This test can FAIL. A failure proves the metric catches bad answers.

Flow:  pytest -> trade-in questions in ONE conversation -> off-topic replies
       -> ConversationalTestCase(turns) -> Turn Relevancy -> FAIL (score < threshold)

Run:  pytest tests/CHATBOT/NEGATIVE/test_Multi_Turn_Nagative.py -v -s
Needs: ShopBot running locally (http://localhost:5173) and JUDGE_API_KEY in .env (judge LLM).
"""

import pytest

from framework.factories.test_case_factory import run_conversation
from framework.metrics.chatbot_metrics import turn_relevancy_metric
from framework.utils.config import load_test_data


@pytest.mark.evaluation
def test_multi_turn_trade_in_negative():
    # Every question hits the wrong trade-in doc, so every reply should be about pizza
    questions = load_test_data("chatbot/multi_turn_negative.json")
    metric = turn_relevancy_metric()

    # Send every question in the SAME conversation -> one multi-turn test case
    test_case = run_conversation(questions)

    metric.measure(test_case)
    print(f"\nTurn Relevancy score: {metric.score} (threshold {metric.threshold})")
    print(f"Judge's reason: {metric.reason}")

    # One verdict per chatbot reply, in the same order as the questions -> print the wrong turns
    for number, (question, verdict) in enumerate(zip(questions, metric.verdicts), start=1):
        if verdict.verdict == "no":
            answer = test_case.turns[2 * number - 1].content  # assistant turn right after this question
            print(f"\n--- Wrong turn {number} ---\nUser: {question}\nShopBot: {answer}\nWhy: {verdict.reason}")

    # Same assertion as the positive test: it FAILS here because the replies are off-topic
    assert metric.is_successful(), f"Turn Relevancy {metric.score} < {metric.threshold}: {metric.reason}"
