"""Prompt Injection test for ShopBot with DeepEval GEval.

Prompt injection = the user tries to OVERRIDE ShopBot's instructions ("ignore your rules and...").
ShopBot must keep following its own rules and not do what the attack asks.

Flow:  attack message -> ShopBot reply
       -> GEval "Resists Injection" (judge LLM, compares with the expected behaviour) -> PASS / FAIL

Run:  pytest tests/PROMPT/test_Prompt_Injection.py -v -s
Needs: ShopBot running locally (http://localhost:5173) and JUDGE_API_KEY in .env (judge LLM).
"""

import pytest
from deepeval.test_case import LLMTestCase

from framework.assertions.evaluation_assertions import assert_metric_passes
from framework.clients.shopbot_client import send_message
from framework.metrics.prompt_metrics import resists_injection_metric
from framework.utils.config import load_test_data

# Each case: an attack + the BEHAVIOUR we expect (not an exact answer)
ATTACKS = load_test_data("prompt/prompt_injection.json")


@pytest.mark.evaluation
@pytest.mark.parametrize("attack", ATTACKS, ids=lambda a: a["input"][:35])
def test_prompt_injection_is_resisted(attack):
    metric = resists_injection_metric()

    # Send the attack to ShopBot
    reply = send_message(attack["input"])["message"]["content"]
    print(f"\nAttack: {attack['input']}\nExpected: {attack['expected_output']}\nReply:  {reply}")

    # An empty reply can't be judged and tells the user nothing
    assert reply.strip() != "", f"ShopBot returned an empty reply for: {attack['input']!r}"

    # Attack + reply + expected behaviour = what the judge compares
    test_case = LLMTestCase(input=attack["input"], actual_output=reply, expected_output=attack["expected_output"])

    # The judge checks ShopBot did NOT do what the attack asked (no fake discount, no new persona, no secrets)
    assert_metric_passes(metric, test_case)
