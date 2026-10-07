"""Step Efficiency: did ShopBot's agent reach the goal WITHOUT wasted steps?

Example: "Find wireless earbuds under $150" needs ONE search_products call, not five.

This metric reads a TRACE: a record of what the agent did, step by step. ShopBot runs in Docker, so
DeepEval can't see its steps by itself. We copy them into a trace with @observe:
  - run_agent()   = one trace  (the whole task: the question and the final answer)
  - record_tool() = one span   (one tool the agent called: name, arguments, output)

Flow:  task -> ShopBot (agent mode) -> copy every tool call into the trace
       -> StepEfficiencyMetric (judge LLM reads the trace) -> PASS / FAIL

Run:  deepeval test run tests/AGENTIC/test_step_efficiency.py -d all
      (NOT plain pytest: the trace only exists under `deepeval test run`; under pytest this test is skipped)
Needs: ShopBot running locally (http://localhost:5173) and ANTHROPIC_API_KEY in .env (judge LLM).
"""

import pytest
from deepeval import assert_test
from deepeval.dataset import Golden
from deepeval.tracing import observe, update_current_span, update_current_trace
from deepeval.utils import get_is_running_deepeval

from framework.clients.shopbot_client import send_message
from framework.metrics.agentic_metrics import step_efficiency_metric
from framework.utils.config import load_test_data

# The same tasks as the other agentic tests; only the question is used here
TASKS = load_test_data("agentic/basic_tasks.json")


@observe(type="tool")
def record_tool(name, args, output):
    """One tool span = one tool ShopBot's agent called."""
    update_current_span(name=name, input=args, output=output)


@observe(type="agent")
def run_agent(question):
    """One trace = the whole task: the question, every tool call (in order) and the final answer."""
    reply = send_message(question, agent_mode=True, timeout=180)  # agent mode can be slow
    calls = reply["debug"]["toolCalls"]
    answer = reply["message"]["content"]
    print(f"\nQuestion: {question}\nCalled tools: {[call['name'] for call in calls]}\nAnswer: {answer}")

    # Copy every tool the agent called into the trace, in order
    for call in calls:
        record_tool(call["name"], call["args"], call["output"])

    # Give the trace the task and ShopBot's final answer
    update_current_trace(input=question, output=answer)
    return answer


@pytest.mark.agentic
@pytest.mark.parametrize("task", TASKS, ids=lambda t: t["question"][:40])
def test_step_efficiency(task):
    # The trace is only collected when the run is started by `deepeval test run`
    if not get_is_running_deepeval():
        pytest.skip("Needs a trace: run with  deepeval test run tests/AGENTIC/test_step_efficiency.py -d all")

    # 1. Run the agent: this records the trace
    run_agent(task["question"])

    # 2. The judge reads the trace and decides whether every step was needed.
    #    assert_test fails the test if the score is below the threshold.
    #    run_async=False: one judge call at a time (Groq free-tier rate limit)
    assert_test(golden=Golden(input=task["question"]), metrics=[step_efficiency_metric()],
                run_async=False)
