"""Single-turn chat evaluation for ShopBot with DeepEval.

Single turn = ONE question -> ONE response, evaluated as a DeepEval LLMTestCase
(multi-turn conversations use ConversationalTestCase instead).

Flow:  pytest -> send question -> Chatbot API -> actual response
       -> LLMTestCase -> Answer Relevancy -> PASS / FAIL

Run:  pytest tests/CHATBOT/test_single_turn_and_turn_relevancy.py -v -s
Needs: ShopBot running locally (http://localhost:5173) and ANTHROPIC_API_KEY in .env (judge LLM).
"""

import pytest
from deepeval.test_case import LLMTestCase

from framework.assertions.evaluation_assertions import assert_metric_passes
from framework.clients.shopbot_client import send_message
from framework.metrics.chatbot_metrics import answer_relevancy_metric


@pytest.mark.evaluation
def test_single_turn_return_policy():
    question = "What is your return policy for electronics?"
    metric = answer_relevancy_metric()

    # Send question -> receive the chatbot's actual response (one turn)
    reply = send_message(question)
    actual_response = reply["message"]["content"]
    print(f"\nQuestion: {question}\nActual response: {actual_response}")

    # One question + one response = a single-turn test case
    test_case = LLMTestCase(input=question, actual_output=actual_response)

    # Evaluate the single turn with Answer Relevancy -> PASS / FAIL
    assert_metric_passes(metric, test_case)
    # metric.is_successful() is True when the score is at or above the threshold.
    # LLMTestCase is DeepEval's container for one question and one answer. Metrics do not accept plain strings; 
        # they accept a test case.