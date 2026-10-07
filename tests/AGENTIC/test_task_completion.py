"""Task Completion: did ShopBot's agent complete the customer's task?

Agent mode = the LLM chooses ShopBot's tools itself. The judge reads what the agent did (its tool calls
and their outputs) and its final answer, works out the task from the question, and decides whether the
task was completed. No expected answer is needed.

Flow:  task -> ShopBot (agent mode) -> tools called + final answer
       -> LLMTestCase -> TaskCompletionMetric (judge LLM) -> PASS / FAIL

Run:  pytest tests/AGENTIC/test_task_completion.py -v -s
Needs: ShopBot running locally (http://localhost:5173) and ANTHROPIC_API_KEY in .env (judge LLM).
"""

import pytest

from framework.assertions.evaluation_assertions import assert_metric_passes
from framework.factories.test_case_factory import agent_test_case
from framework.metrics.agentic_metrics import task_completion_metric
from framework.utils.config import load_test_data

# The same tasks as the Tool Correctness test; only the question is used here
TASKS = load_test_data("agentic/basic_tasks.json")


@pytest.mark.agentic
@pytest.mark.parametrize("task", TASKS, ids=lambda t: t["question"][:40])
def test_task_completion(task):
    metric = task_completion_metric()

    # Ask ShopBot in agent mode: the test case holds the question, the tools it called and its answer
    test_case = agent_test_case(task["question"])

    # An empty answer can't be judged and tells the customer nothing
    assert test_case.actual_output.strip() != "", f"ShopBot returned an empty answer for: {task['question']!r}"

    # The judge decides whether the customer's task was completed
    assert_metric_passes(metric, test_case)
