"""S-03 Toxic / Harmful Response: ShopBot must never produce abusive or hateful content,
even when the user asks for it.

Built-in check: DeepEval's ToxicityMetric. The judge looks for insults, hate, threats or
mockery in the REPLY (a toxic request is fine; a toxic reply is not).
Score 1 = not toxic (PASS), lower = toxic content found.

Flow:  request for abusive / hateful content -> ShopBot reply
       -> LLMTestCase -> ToxicityMetric (judge LLM) -> PASS / FAIL

Run:  pytest tests/SECURITY_GUARDRAILS/test_toxicity.py -v -s
Needs: ShopBot running locally (http://localhost:5173) and ANTHROPIC_API_KEY in .env (judge LLM).
"""

import pytest
from deepeval.test_case import LLMTestCase

from framework.assertions.evaluation_assertions import assert_metric_passes
from framework.clients.shopbot_client import send_message
from framework.metrics.security_metrics import toxicity_metric
from framework.utils.config import load_test_data

# Requests for abusive or hateful content
ATTACKS = load_test_data("security/toxicity.json")


@pytest.mark.evaluation
@pytest.mark.parametrize("attack", ATTACKS, ids=lambda text: text[:40])
def test_no_toxic_response(attack):
    metric = toxicity_metric()

    # 1. Ask ShopBot for abusive / hateful content
    reply = send_message(attack)["message"]["content"]
    print(f"\nInput: {attack}\nReply: {reply}")

    # An empty reply can't be judged and tells the user nothing
    assert reply.strip() != "", f"ShopBot returned an empty reply for: {attack!r}"

    # 2. Test case: input + reply
    test_case = LLMTestCase(input=attack, actual_output=reply)

    # 3. The judge checks the reply for toxic content
    assert_metric_passes(metric, test_case)
