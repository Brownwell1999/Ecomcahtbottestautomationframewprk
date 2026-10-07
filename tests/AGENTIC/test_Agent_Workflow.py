"""Agent Workflow: did ShopBot's agent take the RIGHT STEPS in the RIGHT ORDER?

A final answer can look fine while the agent's execution was poor. Example task:
"Show me the full details of the Sonix Pro Wireless Earbuds"
    good:  search_products (find the product)  ->  get_products (fetch its details)
    bad:   get_products with a guessed id, or the same search repeated again and again
So we grade the WORKFLOW (the ordered tool calls), not only the answer.

There is no built-in metric for this, so we use our own GEval metric "Agent Workflow"
(framework/metrics/agentic_metrics.py): the rules of a good workflow, written in plain English.

Test 1: the real agent              -> its workflow must score at or above the threshold
Test 2: a hand-made BAD workflow    -> the metric must FAIL it (proves the metric catches bad agents)

Run:  pytest tests/AGENTIC/test_Agent_Workflow.py -v -s
Needs: ShopBot running locally (http://localhost:5173) and ANTHROPIC_API_KEY in .env (judge LLM).
"""

import pytest
from deepeval.test_case import LLMTestCase, ToolCall

from framework.assertions.evaluation_assertions import assert_metric_passes
from framework.factories.test_case_factory import agent_test_case
from framework.metrics.agentic_metrics import agent_workflow_metric

TASK = "Show me the full details of the Sonix Pro Wireless Earbuds"
EXPECTED_TOOLS = ["search_products", "get_products"]  # the workflow we expect, in order


# ---------- Test 1: the real agent ----------
@pytest.mark.agentic
def test_agent_workflow():
    metric = agent_workflow_metric()

    # Ask ShopBot in agent mode: the test case holds every tool it called (in order) and the tools we expected
    test_case = agent_test_case(TASK, expected_tools=EXPECTED_TOOLS)
    workflow = [tool.name for tool in test_case.tools_called]
    print(f"Workflow: {workflow}\nExpected: {EXPECTED_TOOLS}")

    # The judge compares the workflow with the rules of a good workflow
    assert_metric_passes(metric, test_case)


# ---------- Test 2: the metric must catch a bad workflow ----------
@pytest.mark.agentic
def test_metric_fails_bad_workflow():
    metric = agent_workflow_metric()

    # A hand-made BAD workflow (no ShopBot call): guessed id, then the same search twice, then the details
    bad_calls = [
        ToolCall(name="get_products", input_parameters={"ids": [12345]}, output=[]),
        ToolCall(name="search_products", input_parameters={"query": "headphones"}, output={"items": []}),
        ToolCall(name="search_products", input_parameters={"query": "headphones"}, output={"items": []}),
        ToolCall(name="get_products", input_parameters={"ids": [12345]}, output=[]),
    ]
    test_case = LLMTestCase(
        input=TASK,
        actual_output="Here are the full details of the Sonix Pro Wireless Earbuds: $123.95, rated 3.8.",  # LOOKS fine
        tools_called=bad_calls,
        expected_tools=[ToolCall(name=name) for name in EXPECTED_TOOLS],
    )

    metric.measure(test_case)
    print(f"\nBad workflow: {[call.name for call in bad_calls]}")
    print(f"Agent Workflow score: {metric.score} (threshold {metric.threshold})")
    print(f"Reason: {metric.reason}")

    # The opposite assertion: this workflow is bad, so a PASSING score would mean the metric is useless
    assert not metric.is_successful(), f"The metric did not catch the bad workflow (score {metric.score})"
