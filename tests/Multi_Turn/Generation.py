"""Multi-turn GENERATION tests for ShopBot with DeepEval.

Metrics (one test each):
  Turn Faithfulness = in every turn, is the reply supported by the retrieved chunks (no hallucination)?
  Turn Relevancy    = in every turn, does the reply answer what the user asked?
                      (the multi-turn version of Answer Relevancy)

Flow:  questions in ONE conversation -> each reply + its retrieved chunks -> Turns
       -> ConversationalTestCase -> metric -> PASS / FAIL

Run:  pytest tests/Multi_Turn/Generation.py -v -s
      (this file name doesn't start with test_, so pytest only runs it when you give the path)
Needs: ShopBot running locally (http://localhost:5173, debug block is only returned in dev)
       and ANTHROPIC_API_KEY in .env (judge LLM).
"""

import pytest

from framework.assertions.evaluation_assertions import assert_metric_passes
from framework.factories.test_case_factory import run_conversation
from framework.metrics.chatbot_metrics import turn_relevancy_metric
from framework.metrics.rag_metrics import turn_faithfulness_metric
from framework.utils.config import load_test_data

# Every question is answered from the knowledge base, so every turn has retrieved chunks
QUESTIONS = load_test_data("rag/multi_turn_rag.json")


@pytest.fixture(scope="module")
def conversation():
    """Run the conversation ONCE (keeping each reply's chunks); both metrics judge this same conversation."""
    return run_conversation(QUESTIONS, with_chunks=True)


@pytest.mark.evaluation
def test_turn_faithfulness(conversation):
    # In every turn, is the reply backed by the chunks retrieved for that turn?
    assert_metric_passes(turn_faithfulness_metric(), conversation)


@pytest.mark.evaluation
def test_turn_answer_relevancy(conversation):
    # In every turn, does the reply answer what the user asked?
    assert_metric_passes(turn_relevancy_metric(), conversation)
