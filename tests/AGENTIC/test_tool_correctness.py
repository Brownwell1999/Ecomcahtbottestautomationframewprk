"""Tool Correctness: does ShopBot's agent call the RIGHT tools?

Agent mode = the LLM chooses ShopBot's tools itself (search_products, get_products, add_to_cart...).
Example: "Find wireless earbuds under $150" -> the agent should call the search_products tool.

Flow:  question -> ShopBot (agent mode) -> the tools it really called
       -> LLMTestCase(tools_called, expected_tools) -> ToolCorrectnessMetric -> PASS / FAIL

Run:  pytest tests/AGENTIC/test_tool_correctness.py -v -s
Needs: ShopBot running locally (http://localhost:5173) and JUDGE_API_KEY in .env (judge LLM).
"""

import pytest

from framework.assertions.evaluation_assertions import assert_metric_passes
from framework.factories.test_case_factory import agent_test_case
from framework.metrics.agentic_metrics import tool_correctness_metric
from framework.utils.config import load_test_data

# Each task: a question + the tools we expect the agent to call
TASKS = load_test_data("agentic/basic_tasks.json")


@pytest.mark.agentic
@pytest.mark.parametrize("task", TASKS, ids=lambda t: t["question"][:40])
def test_tool_correctness(task):
    metric = tool_correctness_metric()

    # Ask ShopBot in agent mode: the test case holds the tools it called AND the tools we expected
    test_case = agent_test_case(task["question"], expected_tools=task["expected_tools"])
    called = [tool.name for tool in test_case.tools_called]
    print(f"Expected tools: {task['expected_tools']}")

    # An agent that answered without calling any tool can't be judged on tool use
    assert called != [], f"ShopBot's agent called no tools for: {task['question']!r}"

    # The metric compares the tools called with the tools expected
    assert_metric_passes(metric, test_case)
