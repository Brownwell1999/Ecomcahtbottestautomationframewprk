"""Grounding (Faithfulness) test for ShopBot with DeepEval FaithfulnessMetric.

ShopBot's RAG prompt says: "Answer the question using ONLY the policy excerpts below."
FaithfulnessMetric checks every claim in the answer is supported by the chunks ShopBot retrieved
(debug.retrievalContext). A claim that isn't in the chunks = the prompt rule was broken.

Flow:  policy question -> ShopBot answer + the chunks it retrieved -> LLMTestCase
       -> Faithfulness (judge LLM) -> PASS / FAIL

Run:  pytest tests/PROMPT/test_Faithfulness.py -v -s
Needs: ShopBot running locally (http://localhost:5173, debug block is only returned in dev)
       and JUDGE_API_KEY in .env (judge LLM).
"""

import pytest

from framework.assertions.evaluation_assertions import assert_metric_passes
from framework.factories.test_case_factory import rag_test_case
from framework.metrics.rag_metrics import faithfulness_metric
from framework.utils.config import load_test_data

# Policy questions: answered from the knowledge base, so each has retrieved chunks
QUESTIONS = load_test_data("prompt/faithfulness.json")


@pytest.mark.evaluation
@pytest.mark.parametrize("question", QUESTIONS, ids=lambda q: q[:35])
def test_faithfulness(question):
    metric = faithfulness_metric()

    # Ask ShopBot -> test case with the answer and the chunks it used. Faithfulness needs no golden
    # answer (it compares the answer with the chunks), so expected_output is None.
    test_case = rag_test_case(question, None)

    # The judge splits the answer into claims and checks each one against the chunks
    assert_metric_passes(metric, test_case)
