"""RAG evaluation of ShopBot with DeepEval's EvaluationDataset (goldens) + assert_test.

Metrics: Contextual Relevancy, Contextual Recall, Contextual Precision (retriever)
         Answer Relevancy, Faithfulness (generator)

Flow:  EvaluationDataset(goldens) -> pytest runs one test per golden
       -> ShopBot answer + retrieved chunks (debug.retrievalContext) -> LLMTestCase
       -> assert_test runs all five metrics -> PASS only if EVERY metric passes

Run:  pytest tests/RAG/test_RAG_Retrival_Evaluationdataset_metrix.py -v -s
Needs: ShopBot running locally (http://localhost:5173, debug block is only returned in dev)
       and ANTHROPIC_API_KEY in .env (judge LLM).
"""

import pytest
from deepeval import assert_test
from deepeval.dataset import EvaluationDataset, Golden

from framework.factories.test_case_factory import rag_test_case
from framework.metrics.chatbot_metrics import answer_relevancy_metric
from framework.metrics.rag_metrics import (
    contextual_precision_metric,
    contextual_recall_metric,
    contextual_relevancy_metric,
    faithfulness_metric,
)
from framework.utils.config import load_test_data

# Goldens: question + correct answer (from ShopBot's data/knowledge_base/*.md)
dataset = EvaluationDataset(goldens=[Golden(**item) for item in load_test_data("rag/rag_goldens.json")])


@pytest.mark.evaluation
@pytest.mark.parametrize("golden", dataset.goldens, ids=lambda g: g.input[:40])
def test_rag_metrics(golden):
    # Ask ShopBot -> answer + the chunks its retriever found, packed with the golden answer
    test_case = rag_test_case(golden.input, golden.expected_output)

    # run_async=False: one judge call at a time (Groq free-tier rate limit)
    assert_test(
        test_case,
        [
            contextual_relevancy_metric(),
            contextual_recall_metric(),
            contextual_precision_metric(),
            answer_relevancy_metric(),
            faithfulness_metric(),
        ],
        run_async=False,
    )

    """
    run_async = False makes the judge calls go one after another instead of all at once, 
    to stay inside Groq's free tokens-per-minute limit.
    """
