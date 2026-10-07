"""Knowledge Retention test for ShopBot with DeepEval.

Knowledge Retention = does the bot REMEMBER facts the user gave earlier in the conversation
(and not forget them or ask for them again)?

Flow:  pytest -> user gives a fact (name) -> other question -> ask about the fact
       -> ConversationalTestCase(turns) -> Knowledge Retention -> PASS / FAIL

Run:  pytest tests/CHATBOT/test_knowledge_retention.py -v -s
Needs: ShopBot running locally (http://localhost:5173) and JUDGE_API_KEY in .env (judge LLM).
"""

import pytest

from framework.assertions.evaluation_assertions import assert_metric_passes
from framework.factories.test_case_factory import run_conversation
from framework.metrics.chatbot_metrics import knowledge_retention_metric
from framework.utils.config import load_test_data


@pytest.mark.evaluation
def test_knowledge_retention_name():
    # Turn 1 gives a fact (name), turn 2 changes topic, turn 3 checks the bot still remembers it
    questions = load_test_data("chatbot/knowledge_retention.json")
    metric = knowledge_retention_metric()

    # Send every question in the SAME conversation -> one multi-turn test case
    test_case = run_conversation(questions)

    # Evaluate: did the bot keep the fact the user gave (name = Deepak) without forgetting it?
    assert_metric_passes(metric, test_case)
