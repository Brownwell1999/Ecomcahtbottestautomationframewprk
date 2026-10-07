"""Functions for reading ShopBot's live traces from LangSmith and writing scores back onto them.

ShopBot records every conversation turn in LangSmith as a trace named "shopbot-turn".
LangSmith is only the SOURCE of traces here; all scoring is done by DeepEval (online_eval/)."""

from datetime import datetime, timedelta, timezone

from langsmith import Client

from framework.utils.config import LANGSMITH_API_KEY, LANGSMITH_PROJECT


def recent_turns(hours=24, limit=100):
    """Return ShopBot's most recent conversation turns from the last `hours` hours, newest first.
    Each turn is a plain dict: {"run_id", "question", "answer", "retrieval_context", "intent"}."""
    client = Client(api_key=LANGSMITH_API_KEY)
    runs = client.list_runs(
        project_name=LANGSMITH_PROJECT,
        is_root=True,                               # the whole turn, not its inner LLM calls
        filter='eq(name, "shopbot-turn")',
        start_time=datetime.now(timezone.utc) - timedelta(hours=hours),
        limit=limit,
    )

    turns = []
    for run in runs:
        inputs = run.inputs or {}
        outputs = run.outputs or {}
        if run.error or "message" not in inputs or "reply" not in outputs:
            continue  # the turn crashed or is still running: nothing to score

        # The chunks the retriever found; "used" = the ones the answer was actually built from
        chunks = (outputs.get("trace") or {}).get("chunks") or []
        turns.append({
            "run_id": str(run.id),
            "question": inputs["message"],
            "answer": outputs["reply"],
            "retrieval_context": [chunk["content"] for chunk in chunks if chunk.get("used")],
            "intent": (outputs.get("nlu") or {}).get("intent"),
        })
    return turns


def recent_agent_turns(hours=24, limit=50):
    """Return ShopBot's most recent AGENT-mode turns (traces named "shopbot-agent"), newest first.
    Each turn is a plain dict: {"run_id", "question", "answer", "tool_calls"}, where tool_calls is the
    list of tools the agent called, in order: {"name", "args", "output"}.
    In production this replaces the dev-only debug.toolCalls field."""
    client = Client(api_key=LANGSMITH_API_KEY)
    runs = client.list_runs(
        project_name=LANGSMITH_PROJECT,
        is_root=True,
        filter='eq(name, "shopbot-agent")',
        start_time=datetime.now(timezone.utc) - timedelta(hours=hours),
        limit=limit,
    )

    turns = []
    for run in runs:
        inputs = run.inputs or {}
        outputs = run.outputs or {}
        if run.error or "message" not in inputs or "reply" not in outputs:
            continue  # the turn crashed or is still running: nothing to score

        # The tool calls are steps INSIDE the trace: every step of this trace whose type is "tool"
        steps = client.list_runs(project_name=LANGSMITH_PROJECT, trace_id=run.trace_id, run_type="tool")
        tool_calls = [{"name": step.name, "args": step.inputs or {},
                       "output": (step.outputs or {}).get("output", step.outputs)}
                      for step in sorted(steps, key=lambda step: step.start_time)]
        turns.append({"run_id": str(run.id), "question": inputs["message"], "answer": outputs["reply"],
                      "tool_calls": tool_calls})
    return turns


def save_score(run_id, metric_name, score, reason):
    """Write one metric score onto a trace as LangSmith feedback, so it shows next to the trace
    and LangSmith's dashboards and alerts can use it."""
    client = Client(api_key=LANGSMITH_API_KEY)
    client.create_feedback(run_id, key=f"deepeval_{metric_name}", score=score, comment=reason)
