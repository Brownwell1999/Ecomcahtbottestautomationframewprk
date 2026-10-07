"""Negative Conversation Completeness test for ShopBot with DeepEval.

The user asks about the headphone warranty (answered well), then asks a natural follow-up:
the repair cost after the warranty ends. ShopBot's knowledge base has no repair prices, so the
bot can't satisfy that last goal and the score should drop below the threshold.

This test can FAIL. A failure proves the metric catches unsatisfied users.

Flow:  pytest -> warranty questions in ONE conversation -> last reply can't help
       -> ConversationalTestCase(turns) -> Conversation Completeness -> FAIL (score < threshold)

Run:  pytest tests/CHATBOT/NEGATIVE/test_Conversation_Completeness_Negative.py -v -s
Needs: ShopBot running locally (http://localhost:5173) and JUDGE_API_KEY in .env (judge LLM).
"""

import pytest

from framework.assertions.evaluation_assertions import assert_metric_passes
from framework.factories.test_case_factory import run_conversation
from framework.metrics.chatbot_metrics import conversation_completeness_metric
from framework.utils.config import load_test_data


@pytest.mark.evaluation
def test_conversation_completeness_repair_cost_negative():
    # Turns 1-2 are answered from the real warranty doc.
    # Turn 3 is a natural follow-up, but the knowledge base has no repair prices,
    # so the bot can't satisfy the LAST user goal.
    questions = load_test_data("chatbot/conversation_completeness_negative.json")
    metric = conversation_completeness_metric()

    # Send every question in the SAME conversation -> one multi-turn test case
    test_case = run_conversation(questions)

    assert_metric_passes(metric, test_case)
