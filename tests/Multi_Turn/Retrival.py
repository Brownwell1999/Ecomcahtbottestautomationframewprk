"""Multi-turn RETRIEVAL test for ShopBot with DeepEval.

Metric:
  Turn Contextual Relevancy = in every turn, are the chunks the retriever found
                              relevant to what the user asked?

Flow:  questions in ONE conversation -> each reply + its retrieved chunks -> Turns
       -> ConversationalTestCase -> Turn Contextual Relevancy -> PASS / FAIL

Run:  pytest tests/Multi_Turn/Retrival.py -v -s
      (this file name doesn't start with test_, so pytest only runs it when you give the path)
Needs: ShopBot running locally (http://localhost:5173, debug block is only returned in dev)
       and ANTHROPIC_API_KEY in .env (judge LLM).
"""

import pytest

from framework.assertions.evaluation_assertions import assert_metric_passes
from framework.factories.test_case_factory import run_conversation
from framework.metrics.rag_metrics import turn_contextual_relevancy_metric
from framework.utils.config import load_test_data

# Every question is answered from the knowledge base, so every turn has retrieved chunks
QUESTIONS = load_test_data("rag/multi_turn_rag.json")


@pytest.mark.evaluation
def test_turn_contextual_relevancy():
    # 0.5 = DeepEval's default threshold (chunks always carry some extra text)
    metric = turn_contextual_relevancy_metric()

    # Send every question in the SAME conversation, keeping each reply's retrieved chunks
    conversation = run_conversation(QUESTIONS, with_chunks=True)

    assert_metric_passes(metric, conversation)
