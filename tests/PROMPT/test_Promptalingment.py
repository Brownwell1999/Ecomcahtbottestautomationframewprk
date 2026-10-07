"""Prompt Alignment test for ShopBot with DeepEval PromptAlignmentMetric.

Prompt Alignment = does ShopBot's answer FOLLOW the instructions in its system prompt?
The instructions are copied from ShopBot's real system prompt (PERSONA in
C:\\Ecomchatboat\\services\\chat_service\\app\\prompts.py) and live in framework/metrics/prompt_metrics.py.

It checks rules, not facts, so there is no golden answer: only the question and ShopBot's reply.

Flow:  question -> ShopBot reply -> PromptAlignmentMetric (judge LLM checks each instruction) -> PASS / FAIL

Run:  pytest tests/PROMPT/test_Promptalingment.py -v -s
Needs: ShopBot running locally (http://localhost:5173) and ANTHROPIC_API_KEY in .env (judge LLM).
"""

import pytest
from deepeval.test_case import LLMTestCase

from framework.assertions.evaluation_assertions import assert_metric_passes
from framework.clients.shopbot_client import send_message
from framework.metrics.prompt_metrics import prompt_alignment_metric
from framework.utils.config import load_test_data

# Only the input is needed: Prompt Alignment checks the rules, not a golden answer
QUESTIONS = load_test_data("prompt/prompt_alignment.json")


@pytest.mark.evaluation
@pytest.mark.parametrize("question", QUESTIONS, ids=lambda q: q[:35])
def test_prompt_alignment(question):
    metric = prompt_alignment_metric()

    # Ask ShopBot
    reply = send_message(question)["message"]["content"]
    print(f"\nQuestion: {question}\nActual:   {reply}")

    # An empty reply can't be judged and tells the user nothing
    assert reply.strip() != "", f"ShopBot returned an empty reply for: {question!r}"

    # Question + reply: the judge checks the reply against each instruction in ShopBot's prompt
    test_case = LLMTestCase(input=question, actual_output=reply)

    assert_metric_passes(metric, test_case)
