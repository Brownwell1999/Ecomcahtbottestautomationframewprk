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


def save_score(run_id, metric_name, score, reason):
    """Write one metric score onto a trace as LangSmith feedback, so it shows next to the trace
    and LangSmith's dashboards and alerts can use it."""
    client = Client(api_key=LANGSMITH_API_KEY)
    client.create_feedback(run_id, key=f"deepeval_{metric_name}", score=score, comment=reason)
