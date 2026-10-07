"""Multi-turn chat evaluation for ShopBot with DeepEval.

Multi turn = SEVERAL questions in ONE conversation, evaluated as a DeepEval
ConversationalTestCase (a list of user/assistant Turns).

Flow:  pytest -> send question 1 -> get conversationId + response
       -> send question 2 with the same conversationId -> ... (repeat)
       -> ConversationalTestCase(turns) -> Turn Relevancy -> PASS / FAIL

Run:  pytest tests/CHATBOT/test_multi_turn.py -v -s
Needs: ShopBot running locally (http://localhost:5173) and JUDGE_API_KEY in .env (judge LLM).
"""

import pytest

from framework.assertions.evaluation_assertions import assert_metric_passes
from framework.factories.test_case_factory import run_conversation
from framework.metrics.chatbot_metrics import turn_relevancy_metric
from framework.utils.config import load_test_data


@pytest.mark.evaluation
def test_multi_turn_headphones_shopping():
    # Later questions depend on earlier ones ("them", "it"), so the bot must remember context
    questions = load_test_data("chatbot/multi_turn.json")
    metric = turn_relevancy_metric()

    # Send every question in the SAME conversation -> one multi-turn test case
    test_case = run_conversation(questions)

    # Evaluate: is every assistant reply relevant to the conversation so far?
    assert_metric_passes(metric, test_case)
