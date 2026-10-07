"""Answer Relevancy test for ShopBot with DeepEval.

Answer Relevancy = does the answer address the question that was asked?

Flow:  pytest -> 1. send question -> Chatbot API -> 2. actual response -> Python test
       -> 3. pass question + response to DeepEval -> Answer Relevancy -> PASS / FAIL

Run:  pytest tests/CHATBOT/test_answer_relevancy.py -v -s
Needs: ShopBot running locally (http://localhost:5173) and JUDGE_API_KEY in .env (judge LLM).
"""

import pytest
from deepeval.test_case import LLMTestCase

from framework.assertions.evaluation_assertions import assert_metric_passes
from framework.clients.shopbot_client import send_message
from framework.metrics.chatbot_metrics import answer_relevancy_metric
from framework.utils.config import load_test_data

# One test per question (pytest runs the test function once for each)
QUESTIONS = load_test_data("chatbot/answer_relevancy.json")


@pytest.mark.evaluation
@pytest.mark.parametrize("question", QUESTIONS)
def test_answer_relevancy(question):
    metric = answer_relevancy_metric()

    # 1-2. Send the question and get the chatbot's actual response
    reply = send_message(question)
    actual_response = reply["message"]["content"]
    print(f"\nQuestion: {question}\nActual response: {actual_response}")

    # 3. Pass question + response to DeepEval
    test_case = LLMTestCase(input=question, actual_output=actual_response)

    # Answer Relevancy -> PASS / FAIL (fails the test if the score is below the threshold)
    assert_metric_passes(metric, test_case)
