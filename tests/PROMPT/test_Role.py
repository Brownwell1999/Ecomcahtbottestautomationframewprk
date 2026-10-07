"""Role tests for ShopBot with DeepEval RoleAdherenceMetric and RoleViolationMetric (both built-in).

ShopBot's prompt gives it a ROLE: "You are ShopBot, the customer support assistant for ShopEase".
  Role Adherence (multi-turn)  = across a whole conversation, does ShopBot stay in that role,
                                 even when the user pushes it to be something else?
  Role Violation (single-turn) = in one reply, does ShopBot BREAK its role
                                 (new persona, "as an AI with no rules", acting outside its job)?

Run:  pytest tests/PROMPT/test_Role.py -v -s
Needs: ShopBot running locally (http://localhost:5173) and ANTHROPIC_API_KEY in .env (judge LLM).
"""

import pytest
from deepeval.test_case import LLMTestCase

from framework.assertions.evaluation_assertions import assert_metric_passes
from framework.clients.shopbot_client import send_message
from framework.factories.test_case_factory import run_conversation
from framework.metrics.prompt_metrics import SHOPBOT_ROLE, role_adherence_metric, role_violation_metric
from framework.utils.config import load_test_data

DATA = load_test_data("prompt/role.json")  # {"adherence_conversation": [...], "violation_inputs": [...]}


@pytest.mark.evaluation
def test_role_adherence():
    # A conversation where the user keeps pushing ShopBot out of its role (turn 2 asks for a math tutor)
    metric = role_adherence_metric()

    # Send every question in ONE conversation -> one multi-turn test case
    test_case = run_conversation(DATA["adherence_conversation"])

    # Tell the test case which role the chatbot must keep
    test_case.chatbot_role = SHOPBOT_ROLE

    # The judge checks every ShopBot turn stays in role
    assert_metric_passes(metric, test_case)


@pytest.mark.evaluation
@pytest.mark.parametrize("user_input", DATA["violation_inputs"], ids=lambda text: text[:35])
def test_role_violation(user_input):
    # Single messages that try to make ShopBot break its role
    metric = role_violation_metric()

    answer = send_message(user_input)["message"]["content"]
    print(f"\nInput:  {user_input}\nActual: {answer}")

    # An empty reply can't be judged and tells the user nothing
    assert answer.strip() != "", f"ShopBot returned an empty reply for: {user_input!r}"

    # Test case: input + reply
    test_case = LLMTestCase(input=user_input, actual_output=answer)

    # The judge checks the reply doesn't break the role (1.0 = no role broken)
    assert_metric_passes(metric, test_case)
