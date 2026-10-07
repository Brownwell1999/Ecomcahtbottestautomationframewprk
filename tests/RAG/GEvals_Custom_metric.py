"""Custom "Correctness" metric for ShopBot with DeepEval's GEval.

GEval = a metric YOU define in plain English (criteria); the judge LLM scores it 0..1.
Here: does ShopBot's actual answer state the same facts as the expected (golden) answer?

Assertion idea:  Judge LLM compares Expected output -> Actual output

Flow:  EvaluationDataset(goldens) -> pytest runs one test per golden
       -> ShopBot answer -> LLMTestCase(input, actual_output, expected_output)
       -> GEval Correctness -> PASS / FAIL

Run:  pytest tests/RAG/GEvals_Custom_metric.py -v -s
      (this file name doesn't start with test_, so pytest only runs it when you give the path)
Needs: ShopBot running locally (http://localhost:5173) and JUDGE_API_KEY in .env (judge LLM).
"""

import pytest
from deepeval.dataset import EvaluationDataset, Golden
from deepeval.test_case import LLMTestCase

from framework.assertions.evaluation_assertions import assert_metric_passes
from framework.clients.shopbot_client import send_message
from framework.metrics.llm_metrics import correctness_metric
from framework.utils.config import load_test_data

# Goldens: question + correct answer (from ShopBot's data/knowledge_base/*.md)
dataset = EvaluationDataset(goldens=[Golden(**item) for item in load_test_data("rag/geval_goldens.json")])


@pytest.mark.evaluation
@pytest.mark.parametrize("golden", dataset.goldens, ids=lambda g: g.input[:40])
def test_geval_correctness(golden):
    metric = correctness_metric()

    # Ask ShopBot the golden's question
    reply = send_message(golden.input)
    actual_response = reply["message"]["content"]
    print(f"\nQuestion: {golden.input}\nExpected: {golden.expected_output}\nActual:   {actual_response}")

    # Question + actual answer + golden answer = what the judge compares
    test_case = LLMTestCase(input=golden.input, actual_output=actual_response,
                            expected_output=golden.expected_output)

    # The judge scores the answer against the criteria (0 to 1)
    assert_metric_passes(metric, test_case)
