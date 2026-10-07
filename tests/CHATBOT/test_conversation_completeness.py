"""Conversation Completeness test for ShopBot with DeepEval.

Conversation Completeness = did the bot SATISFY everything the user asked for across the
whole conversation (no question left unanswered)?

Flow:  pytest -> several questions in ONE conversation -> replies
       -> ConversationalTestCase(turns) -> Conversation Completeness -> PASS / FAIL

Run:  pytest tests/CHATBOT/test_conversation_completeness.py -v -s
Needs: ShopBot running locally (http://localhost:5173) and ANTHROPIC_API_KEY in .env (judge LLM).
"""

import pytest

from framework.assertions.evaluation_assertions import assert_metric_passes
from framework.factories.test_case_factory import run_conversation
from framework.metrics.chatbot_metrics import conversation_completeness_metric
from framework.utils.config import load_test_data


@pytest.mark.evaluation
def test_conversation_completeness_warranty():
    # The user has 3 needs about the headphone warranty; the bot must answer all of them
    questions = load_test_data("chatbot/conversation_completeness.json")
    metric = conversation_completeness_metric()

    # Send every question in the SAME conversation -> one multi-turn test case
    test_case = run_conversation(questions)

    # Evaluate: were all of the user's intentions in the conversation satisfied?
    assert_metric_passes(metric, test_case)
