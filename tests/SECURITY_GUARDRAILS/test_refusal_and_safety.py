"""S-04 Unsafe Request / Refusal: ShopBot must NOT perform actions it isn't allowed to do,
even when the user insists over several messages.

Custom check: ConversationalGEval (judges the WHOLE conversation). Each scenario has the user's messages
(the user keeps pushing) and the expected outcome.

Flow:  scenario's user messages -> sent to ShopBot in ONE conversation -> ConversationalTestCase
       (+ scenario + expected outcome) -> ConversationalGEval "Refuses Unsafe Action" -> PASS / FAIL

Run:  pytest tests/SECURITY_GUARDRAILS/test_refusal_and_safety.py -v -s
Needs: ShopBot running locally (http://localhost:5173) and JUDGE_API_KEY in .env (judge LLM).
"""

import pytest

from framework.assertions.evaluation_assertions import assert_metric_passes
from framework.factories.test_case_factory import run_conversation
from framework.metrics.security_metrics import refuses_unsafe_action_metric
from framework.utils.config import load_test_data

# Each scenario: what the user wants, the messages they send (they keep pushing), what must happen
SCENARIOS = load_test_data("security/unsafe_requests.json")


@pytest.mark.evaluation
@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s["scenario"][:40])
def test_refuses_unsafe_request(scenario):
    metric = refuses_unsafe_action_metric()

    # 1. Send the user's messages to ShopBot in ONE conversation, recording both sides
    test_case = run_conversation(scenario["user_messages"])

    # 2. Add the scenario and expected outcome, so the judge knows what ShopBot must NOT do
    test_case.scenario = scenario["scenario"]
    test_case.expected_outcome = scenario["expected_outcome"]

    # 3. The judge scores the whole conversation (0 to 1)
    assert_metric_passes(metric, test_case)
