"""S-02 PII / Sensitive Data Leakage: ShopBot must never repeat, store or reveal personal data.

PII = Personally Identifiable Information (card numbers, CVV, passwords, emails, addresses...).
Built-in check: DeepEval's PIILeakageMetric. The judge looks for personal data in the REPLY
(card numbers, CVV, passwords, emails, addresses, other customers' details).
Score 1 = no leakage (PASS), lower = something leaked.
All personal data in the test inputs is FAKE (4111... is a standard test card number).

Flow:  input with (or asking for) personal data -> ShopBot reply
       -> LLMTestCase -> PIILeakageMetric (judge LLM) -> PASS / FAIL

Run:  pytest tests/SECURITY_GUARDRAILS/test_pii_leakage.py -v -s
Needs: ShopBot running locally (http://localhost:5173) and JUDGE_API_KEY in .env (judge LLM).
"""

import pytest
from deepeval.test_case import LLMTestCase

from framework.assertions.evaluation_assertions import assert_metric_passes
from framework.clients.shopbot_client import send_message
from framework.metrics.security_metrics import pii_leakage_metric
from framework.utils.config import load_test_data

# Messages that contain, or ask for, personal data (all fake)
ATTACKS = load_test_data("security/pii_leakage.json")


@pytest.mark.evaluation
@pytest.mark.parametrize("attack", ATTACKS, ids=lambda text: text[:40])
def test_no_pii_leakage(attack):
    metric = pii_leakage_metric()

    # 1. Send the message with (or asking for) personal data
    reply = send_message(attack)["message"]["content"]
    print(f"\nInput: {attack}\nReply: {reply}")

    # An empty reply can't be judged and tells the user nothing
    assert reply.strip() != "", f"ShopBot returned an empty reply for: {attack!r}"

    # 2. Test case: input + reply
    test_case = LLMTestCase(input=attack, actual_output=reply)

    # 3. The judge checks the reply for personal data
    assert_metric_passes(metric, test_case)
