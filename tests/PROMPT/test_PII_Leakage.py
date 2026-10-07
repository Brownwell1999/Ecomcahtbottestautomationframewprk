"""PII Leakage test for ShopBot with DeepEval PIILeakageMetric (built-in).

PII = Personally Identifiable Information (card numbers, passwords, emails, addresses...).
ShopBot's prompt says: "Never ask for or repeat full card numbers, CVV codes or passwords."
PIILeakageMetric checks the REPLY doesn't expose personal data: card numbers, passwords,
emails, addresses or other customers' details. Score 1 = no leakage (PASS), lower = something leaked.

Flow:  input with (or asking for) personal data -> ShopBot reply
       -> PIILeakageMetric (judge LLM) -> PASS / FAIL

Run:  pytest tests/PROMPT/test_PII_Leakage.py -v -s
Needs: ShopBot running locally (http://localhost:5173) and ANTHROPIC_API_KEY in .env (judge LLM).
All personal data in the test inputs is fake (4111... is a standard test card number).
"""

import pytest
from deepeval.test_case import LLMTestCase

from framework.assertions.evaluation_assertions import assert_metric_passes
from framework.clients.shopbot_client import send_message
from framework.metrics.security_metrics import pii_leakage_metric
from framework.utils.config import load_test_data

# Inputs that try to make ShopBot repeat or reveal personal data (all fake)
INPUTS = load_test_data("prompt/pii_leakage.json")


@pytest.mark.evaluation
@pytest.mark.parametrize("user_input", INPUTS, ids=lambda text: text[:35])
def test_no_pii_leakage(user_input):
    metric = pii_leakage_metric()

    # Send the message with (or asking for) personal data
    reply = send_message(user_input)["message"]["content"]
    print(f"\nInput: {user_input}\nReply: {reply}")

    # An empty reply can't be judged and tells the user nothing
    assert reply.strip() != "", f"ShopBot returned an empty reply for: {user_input!r}"

    # Test case: input + reply (PII leakage is judged on the reply only)
    test_case = LLMTestCase(input=user_input, actual_output=reply)

    # The judge looks for personal data in the reply
    assert_metric_passes(metric, test_case)
