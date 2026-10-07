"""Tone test for ShopBot with DeepEval GEval.

ShopBot's prompt says: "Be friendly and concise". Even when customers are angry or rude,
ShopBot must stay calm, polite and helpful - never rude, sarcastic or defensive.

Flow:  angry customer message -> ShopBot reply
       -> GEval "Tone" (judge LLM reads the message and the reply) -> PASS / FAIL

Run:  pytest tests/PROMPT/test_Tone.py -v -s
Needs: ShopBot running locally (http://localhost:5173) and JUDGE_API_KEY in .env (judge LLM).
"""

import pytest
from deepeval.test_case import LLMTestCase

from framework.assertions.evaluation_assertions import assert_metric_passes
from framework.clients.shopbot_client import send_message
from framework.metrics.prompt_metrics import tone_metric
from framework.utils.config import load_test_data

# Angry / rude customers: the input is the only thing needed (Tone has no golden answer)
MESSAGES = load_test_data("prompt/tone.json")


@pytest.mark.evaluation
@pytest.mark.parametrize("message", MESSAGES, ids=lambda text: text[:35])
def test_tone_with_angry_customer(message):
    metric = tone_metric()

    # Send the angry message
    reply = send_message(message)["message"]["content"]
    print(f"\nInput:  {message}\nActual: {reply}")

    # An empty reply can't be judged and tells the user nothing
    assert reply.strip() != "", f"ShopBot returned an empty reply for: {message!r}"

    # Test case: the angry message + ShopBot's reply
    test_case = LLMTestCase(input=message, actual_output=reply)

    # The judge checks the reply is polite, calm, not defensive, and tries to help
    assert_metric_passes(metric, test_case)
