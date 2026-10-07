"""Multi-turn chatbot tests for ShopBot with DeepEval.

Metrics (one test each):
  Turn Relevancy            = is every reply relevant to the conversation so far?
  Knowledge Retention       = does the bot remember facts the user gave earlier (the name)?
  Conversation Completeness = did the bot satisfy everything the user asked for?

Flow:  questions in ONE conversation -> Turns -> ConversationalTestCase -> metric -> PASS / FAIL

Run:  pytest tests/Multi_Turn/Conversation.py -v -s
      (this file name doesn't start with test_, so pytest only runs it when you give the path)
Needs: ShopBot running locally (http://localhost:5173) and ANTHROPIC_API_KEY in .env (judge LLM).
"""

import pytest

from framework.assertions.evaluation_assertions import assert_metric_passes
from framework.factories.test_case_factory import run_conversation
from framework.metrics.chatbot_metrics import (
    conversation_completeness_metric,
    knowledge_retention_metric,
    turn_relevancy_metric,
)
from framework.utils.config import load_test_data

# The user gives a fact (name), asks about warranty, then checks the bot remembers the name
QUESTIONS = load_test_data("chatbot/multi_turn_conversation.json")


@pytest.fixture(scope="module")
def conversation():
    """Run the conversation ONCE; all three metrics judge this same conversation."""
    return run_conversation(QUESTIONS)


@pytest.mark.evaluation
def test_turn_relevancy(conversation):
    # Is every assistant reply relevant to the conversation so far?
    assert_metric_passes(turn_relevancy_metric(), conversation)


@pytest.mark.evaluation
def test_knowledge_retention(conversation):
    # Did the bot remember the name the user gave in the first message?
    assert_metric_passes(knowledge_retention_metric(), conversation)


@pytest.mark.evaluation
def test_conversation_completeness(conversation):
    # Did the bot satisfy everything the user asked for?
    assert_metric_passes(conversation_completeness_metric(), conversation)
