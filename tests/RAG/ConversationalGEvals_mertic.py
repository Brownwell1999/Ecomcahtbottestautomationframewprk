"""Custom multi-turn metric for ShopBot with DeepEval's ConversationalGEval.

ConversationalGEval = GEval for a WHOLE conversation: you write the criteria in plain English,
the judge LLM reads every turn (role + content) and scores the conversation 0..1.

Flow:  4 questions in ONE ShopBot conversation (conversationId) -> Turns
       -> ConversationalTestCase(turns) -> ConversationalGEval "Correctness" -> PASS / FAIL

Run:  pytest tests/RAG/ConversationalGEvals_mertic.py -v -s
      (this file name doesn't start with test_, so pytest only runs it when you give the path)
Needs: ShopBot running locally (http://localhost:5173) and JUDGE_API_KEY in .env (judge LLM).
"""

import pytest

from framework.assertions.evaluation_assertions import assert_metric_passes
from framework.factories.test_case_factory import run_conversation
from framework.metrics.rag_metrics import conversational_correctness_metric
from framework.utils.config import load_test_data


@pytest.mark.evaluation
def test_conversational_geval_correctness():
    # The last question ("the warranty you just mentioned") tests that the bot remembers its own answer
    questions = load_test_data("rag/conversational_geval.json")
    metric = conversational_correctness_metric()

    # Send every question in the SAME conversation -> one multi-turn test case
    test_case = run_conversation(questions)

    # The judge scores the whole conversation against the criteria
    assert_metric_passes(metric, test_case)
