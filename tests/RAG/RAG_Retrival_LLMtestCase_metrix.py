"""RAG tests for ShopBot with DeepEval: Contextual Relevancy, Recall, Precision, Faithfulness
and Answer Relevancy.

Retriever (the "R" in RAG) - are the chunks ShopBot found good?
  Contextual Relevancy = is the retrieved text relevant to the question?
  Contextual Recall    = did retrieval find everything needed for the correct answer?
  Contextual Precision = are the relevant chunks ranked at the top?
Generator (the "G" in RAG) - is the answer good?
  Faithfulness         = is every claim in the answer supported by the chunks (no hallucination)?
  Answer Relevancy     = does the answer address the question?

Flow:  pytest -> send question -> ShopBot answer + retrieved chunks (debug.retrievalContext)
       -> LLMTestCase(input, actual_output, expected_output, retrieval_context)
       -> one metric per test -> PASS / FAIL

Run:  pytest tests/RAG/RAG_Retrival_LLMtestCase_metrix.py -v -s
      (this file name doesn't start with test_, so pytest only runs it when you give the path)
Needs: ShopBot running locally (http://localhost:5173, debug block is only returned in dev)
       and ANTHROPIC_API_KEY in .env (judge LLM).
"""

import pytest

from framework.assertions.evaluation_assertions import assert_metric_passes
from framework.factories.test_case_factory import rag_test_case
from framework.metrics.chatbot_metrics import answer_relevancy_metric
from framework.metrics.rag_metrics import (
    contextual_precision_metric,
    contextual_recall_metric,
    contextual_relevancy_metric,
    faithfulness_metric,
)
from framework.utils.config import load_test_data

# Question + golden (correct) answer from ShopBot's data/knowledge_base/return_policy.md
RETURN_POLICY = load_test_data("rag/return_policy.json")


@pytest.fixture(scope="module")
def test_case():
    """Ask ShopBot ONCE; all five metrics judge this same answer and the same retrieved chunks."""
    return rag_test_case(RETURN_POLICY["question"], RETURN_POLICY["expected_output"])


@pytest.mark.evaluation
def test_contextual_relevancy_return_policy(test_case):
    # Evaluate: how much of the retrieved text is relevant to the question?
    assert_metric_passes(contextual_relevancy_metric(), test_case)


@pytest.mark.evaluation
def test_contextual_recall_return_policy(test_case):
    # Evaluate: can every sentence of the expected (correct) answer be found in the chunks?
    assert_metric_passes(contextual_recall_metric(), test_case)


@pytest.mark.evaluation
def test_contextual_precision_return_policy(test_case):
    # Evaluate: are the useful chunks ranked above the useless ones?
    assert_metric_passes(contextual_precision_metric(), test_case)


@pytest.mark.evaluation
def test_faithfulness_return_policy(test_case):
    # Evaluate: is every claim in ShopBot's answer backed by the retrieved chunks?
    assert_metric_passes(faithfulness_metric(), test_case)


@pytest.mark.evaluation
def test_answer_relevancy_return_policy(test_case):
    # Evaluate: does ShopBot's answer address the question? (grades the answer, not the chunks)
    assert_metric_passes(answer_relevancy_metric(), test_case)


# How each score is calculated:
#   Contextual Relevancy = relevant statements in the chunks / total statements in the chunks
#   Contextual Recall    = statements in expected_output found in the chunks / total statements in expected_output
#   Contextual Precision = weighted rank score (relevant chunks ranked higher score more)
#   Faithfulness         = claims in actual_output supported by the chunks / total claims in actual_output
#   Answer Relevancy     = relevant statements in actual_output / total statements in actual_output
