"""Negative Knowledge Retention test for ShopBot with DeepEval.

Knowledge Retention = does the bot REMEMBER facts the user gave earlier in the conversation
(and not forget them or ask for them again)?

The user gives facts in turn 1 (wireless earbuds, budget $150). The follow-up questions
("which one", "that one") only make sense if the bot keeps those facts. If it forgets the
budget or the product type, the score drops below the threshold.

This test can FAIL. A failure is the metric catching a real defect (context not carried over).

Flow:  pytest -> user gives facts (earbuds, budget) -> follow-ups that rely on them
       -> ConversationalTestCase(turns) -> Knowledge Retention -> PASS / FAIL

Run:  pytest tests/CHATBOT/test_KnowledgeRetention_Negtive.py -v -s
Needs: ShopBot running locally (http://localhost:5173) and ANTHROPIC_API_KEY in .env (judge LLM).
"""

import pytest

from framework.assertions.evaluation_assertions import assert_metric_passes
from framework.factories.test_case_factory import run_conversation
from framework.metrics.chatbot_metrics import knowledge_retention_metric
from framework.utils.config import load_test_data


@pytest.mark.evaluation
def test_knowledge_retention_budget():
    # Turn 1 gives facts (earbuds, $150 budget); later turns only make sense if the bot remembers them
    questions = load_test_data("chatbot/knowledge_retention_negative.json")
    metric = knowledge_retention_metric()

    # Send every question in the SAME conversation -> one multi-turn test case
    test_case = run_conversation(questions)

    # Evaluate: did the bot keep using the facts the user gave (earbuds, $150) without forgetting them?
    assert_metric_passes(metric, test_case)
