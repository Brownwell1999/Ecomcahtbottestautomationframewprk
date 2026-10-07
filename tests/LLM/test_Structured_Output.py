"""Structured output test for ShopBot's NLU with DeepEval JsonCorrectnessMetric (built-in).

NLU = Natural Language Understanding. ShopBot's NLU step reads the customer's message and returns
JSON (intent + confidence + entities) instead of text; the code then uses that JSON to decide what
to do. Broken JSON = wrong code path.

What we check:
  Part 1 - SHAPE:  JsonCorrectnessMetric checks the JSON matches our Pydantic schema
                   (required fields, right types, intent from the allowed list, confidence from 0 to 1)
  Part 2 - VALUES: plain asserts check the VALUES are right for this message (intent + key entities)

Flow:  message -> ShopBot NLU (/api/chat/eval/nlu) -> JSON -> shape check + value check -> PASS / FAIL

Run:  pytest tests/LLM/test_Structured_Output.py -v -s
Needs: ShopBot running locally (http://localhost:5173, /eval endpoints exist only in dev)
       and JUDGE_API_KEY in .env (the judge only writes the reason for the shape check).
"""

import json
from typing import Literal

import pytest
from deepeval.test_case import LLMTestCase
from pydantic import BaseModel, Field

from framework.assertions.evaluation_assertions import assert_metric_passes
from framework.clients.shopbot_client import nlu
from framework.metrics.llm_metrics import json_correctness_metric
from framework.utils.config import load_test_data


# ---------- The schema the NLU JSON must follow (same as ShopBot's own NLU result) ----------
class Entities(BaseModel):
    order_id: int | None = None
    product_query: str | None = None
    category: Literal["electronics", "fashion", "footwear", "home_kitchen", "beauty", "sports"] | None = None
    brand: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    return_reason: Literal["changed_mind", "defective", "damaged", "wrong_item", "other"] | None = None


class NLUResult(BaseModel):
    intent: Literal["product_search", "order_status", "order_list", "return_request",
                    "policy_question", "human_handoff", "small_talk", "out_of_scope"]
    confidence: float = Field(ge=0, le=1)
    entities: Entities


# Each case: message -> expected intent -> expected entities (only the ones that matter)
CASES = load_test_data("llm/structured_output.json")


@pytest.mark.evaluation
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["message"][:30])
def test_structured_output_nlu(case):
    message = case["message"]
    metric = json_correctness_metric(expected_schema=NLUResult)

    # Ask ShopBot's NLU for its JSON. Keep only the three fields of the schema ("source", "llm_calls" are extras)
    result = nlu(message)
    json_text = json.dumps({"intent": result["intent"], "confidence": result["confidence"],
                            "entities": result["entities"]})
    print(f"\nMessage: {message}\nJSON:    {json_text}")

    # The JSON text is the "actual output" the metric checks
    test_case = LLMTestCase(input=message, actual_output=json_text)

    # Part 1 - SHAPE: valid for the schema? (score 1 = valid, 0 = invalid)
    assert_metric_passes(metric, test_case)

    # Part 2 - VALUES: right intent for this message?
    assert result["intent"] == case["expected_intent"], (
        f"Expected intent {case['expected_intent']}, got {result['intent']}")

    # Part 2 - VALUES: the key entities were found with the right values?
    for name, value in case["expected_entities"].items():
        found = result["entities"].get(name)
        assert found == value, f"Expected {name}={value}, got {found}"
