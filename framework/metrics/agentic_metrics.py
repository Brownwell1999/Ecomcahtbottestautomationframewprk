"""Agentic metrics: judge what ShopBot's agent DID (which tools it called, whether it finished the task)."""

from deepeval.metrics import GEval, StepEfficiencyMetric, TaskCompletionMetric, ToolCorrectnessMetric
from deepeval.test_case import SingleTurnParams

from framework.metrics.chatbot_metrics import judge_llm
from framework.utils.config import THRESHOLDS


def tool_correctness_metric(threshold=THRESHOLDS["metrics"]["tool_correctness"]):
    """Did the agent call the RIGHT tools? Compares the tools called with the tools we expected."""
    return ToolCorrectnessMetric(threshold=threshold, model=judge_llm(), include_reason=True, async_mode=False)


def task_completion_metric(threshold=THRESHOLDS["metrics"]["task_completion"]):
    """Did the agent complete the customer's task? The judge reads what the agent did (its tool calls and
    their outputs) and its final answer, works out the task, and decides whether it was achieved."""
    return TaskCompletionMetric(threshold=threshold, model=judge_llm(), include_reason=True, async_mode=False)


def step_efficiency_metric(threshold=THRESHOLDS["metrics"]["step_efficiency"]):
    """Did the agent reach the goal WITHOUT wasted steps? The judge reads the agent's trace (every tool call,
    in order) and decides whether each step was needed. This metric needs a trace (@observe), not a plain test case."""
    return StepEfficiencyMetric(threshold=threshold, model=judge_llm(), include_reason=True, async_mode=False)


def agent_workflow_metric(threshold=THRESHOLDS["metrics"]["agent_workflow"]):
    """Custom metric (GEval): did the agent take the RIGHT STEPS in the RIGHT ORDER?
    A final answer can look fine while the agent's execution was poor, so we grade the workflow
    (the ordered tool calls), not only the answer. There is no built-in metric for this."""
    return GEval(
        name="Agent Workflow",
        evaluation_steps=[
            "Did the agent call the expected tools in the expected order?",
            "Did it perform every required step (was every expected tool called)?",
            "Did it avoid unnecessary, unrelated or repeated tool calls?",
            "Does the final answer agree with what the tools actually returned?",
        ],
        evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT,
                           SingleTurnParams.TOOLS_CALLED, SingleTurnParams.EXPECTED_TOOLS],
        model=judge_llm(),
        threshold=threshold,
        async_mode=False,
    )
