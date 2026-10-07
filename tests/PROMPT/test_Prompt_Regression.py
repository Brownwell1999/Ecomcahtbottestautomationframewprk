"""Prompt Regression test for ShopBot with DeepEval.

Prompt regression = after someone CHANGES a prompt, is ShopBot still as good as before?
The SAME golden questions run before and after every prompt change. Each test prints the prompt version
that answered, so you can compare two runs. If a metric drops below its threshold, the test fails and the
prompt change should be blocked (a CI quality gate).

Flow:  golden question -> ShopBot answer (+ the prompt version that wrote it)
       -> Correctness + Answer Relevancy (judge LLM) -> PASS only if BOTH pass

Run:  pytest tests/PROMPT/test_Prompt_Regression.py -v -s
      (run it before and after editing C:\\Ecomchatboat\\services\\chat_service\\app\\prompts.py)
Needs: ShopBot running locally (http://localhost:5173, debug block is only returned in dev)
       and ANTHROPIC_API_KEY in .env (judge LLM).
"""

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from framework.clients.shopbot_client import send_message
from framework.metrics.chatbot_metrics import answer_relevancy_metric
from framework.metrics.llm_metrics import correctness_steps_metric
from framework.utils.config import load_test_data

# The regression suite: the same goldens run for every prompt version
GOLDENS = load_test_data("prompt/prompt_regression.json")


@pytest.mark.evaluation
@pytest.mark.parametrize("golden", GOLDENS, ids=lambda g: g["input"][:35])
def test_prompt_regression(golden):
    # Ask ShopBot; promptVersion says which version of its prompts answered (e.g. "v2.2")
    reply = send_message(golden["input"])
    actual_answer = reply["message"]["content"]
    prompt_version = reply["debug"]["promptVersion"]
    print(f"\nPrompt version under test: {prompt_version}")
    print(f"Question: {golden['input']}\nExpected: {golden['expected_output']}\nActual:   {actual_answer}")

    # An empty reply can't be judged and tells the user nothing
    assert actual_answer.strip() != "", f"[prompt {prompt_version}] ShopBot returned an empty reply"

    # Question + actual answer + golden answer = what the judges compare
    test_case = LLMTestCase(input=golden["input"], actual_output=actual_answer,
                            expected_output=golden["expected_output"])

    # Both metrics must pass: the answer is correct (Correctness) AND on-topic (Answer Relevancy).
    # run_async=False: one judge call at a time (Groq free-tier rate limit)
    assert_test(
        test_case,
        [correctness_steps_metric(), answer_relevancy_metric()],
        run_async=False,
    )
