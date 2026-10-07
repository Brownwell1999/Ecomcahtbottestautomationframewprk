"""Collect ShopBot's real failures into a "to review" file, so they can become goldens.

A failed real conversation is the best source of a new test: it is a mistake that actually happened.

Two sources:
  A. Thumbs-down feedback   users clicked "not helpful"; ShopBot saved the question and the answer
  B. Online evaluation      turns that failed a metric in reports/online_eval.json

Flow:  feedback table (rating = -1) + failed online-eval turns
       -> one candidate per failed conversation -> merge into test_data/review/production_failures.json

A candidate is NOT a golden yet. A failed conversation only shows the WRONG answer, so a person must
write the correct `expected_output`, then move the entry into a golden file and raise the dataset version
(test_data/dataset_version.yaml). Entries already in the file are never changed, so your edits are safe.

Run:  python -m dataset_tools.export_production_failures
Needs: nothing for source B. Source A needs ShopBot's Docker running on this machine.
Uses no LLM.
"""

import json
import subprocess
import sys

from framework.utils.config import PROJECT_ROOT, SHOPBOT_DIR, TEST_DATA_DIR

OUTPUT_FILE = TEST_DATA_DIR / "review" / "production_failures.json"
ONLINE_REPORT = PROJECT_ROOT / "reports" / "online_eval.json"

# One JSON list of the thumbs-down rows, newest first
FEEDBACK_QUERY = ("select coalesce(json_agg(t), '[]') from ("
                  "select user_message, bot_message, comment, created_at from feedback "
                  "where rating = -1 order by created_at desc) t")


def thumbs_down_feedback():
    """Source A: the thumbs-down rows from ShopBot's database, as candidates."""
    # ponytail: reads the database through ShopBot's own Docker Compose, so it only works where that
    # Docker runs (this machine). For a deployed ShopBot, replace this with a read API or a database URL.
    command = ["docker", "compose", "exec", "-T", "postgres", "sh", "-c",
               f'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -c "{FEEDBACK_QUERY}"']
    try:
        done = subprocess.run(command, cwd=SHOPBOT_DIR, capture_output=True, text=True,
                              encoding="utf-8", timeout=60)
    except (OSError, subprocess.TimeoutExpired) as problem:
        print(f"Feedback skipped: could not run Docker ({problem}).")
        return []
    if done.returncode != 0:
        print(f"Feedback skipped: ShopBot's database is not reachable ({done.stderr.strip()[:150]}).")
        return []

    candidates = []
    for row in json.loads(done.stdout):
        if row["user_message"] and row["bot_message"]:
            candidates.append({"source": "thumbs_down", "question": row["user_message"],
                               "actual_answer": row["bot_message"],
                               "why": row["comment"] or "The user marked this answer as not helpful."})
    return candidates


def failed_online_turns():
    """Source B: the turns that failed a metric in the last online evaluation report, as candidates."""
    if not ONLINE_REPORT.exists():
        print("Online evaluation skipped: reports/online_eval.json not found (run online_eval first).")
        return []
    candidates = []
    for result in json.loads(ONLINE_REPORT.read_text(encoding="utf-8"))["results"]:
        if result["passed"] is False:
            candidates.append({"source": "online_eval", "question": result["question"],
                               "actual_answer": result.get("answer", ""),
                               "why": f"Failed {result['metric']} (score {result['score']}): {result['reason']}"})
    return candidates


def merge(existing, candidates):
    """Add the candidates that are not in the file yet. The same question + answer from the same source
    counts as one entry. Existing entries (and any edits made to them) are kept as they are."""
    known = {(entry["source"], entry["question"], entry["actual_answer"]) for entry in existing}
    added = []
    for candidate in candidates:
        key = (candidate["source"], candidate["question"], candidate["actual_answer"])
        if key not in known:
            known.add(key)
            added.append({**candidate,
                          "expected_output": "",        # a person writes the correct answer here
                          "status": "needs_review"})    # then: move it to a golden file, or delete it
    return existing + added, len(added)


def main():
    feedback = thumbs_down_feedback()
    online = failed_online_turns()
    print(f"Found {len(feedback)} thumbs-down answers and {len(online)} failed online-evaluation results.")

    existing = json.loads(OUTPUT_FILE.read_text(encoding="utf-8")) if OUTPUT_FILE.exists() else []
    merged, added = merge(existing, feedback + online)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Added {added} new candidates. {OUTPUT_FILE} now has {len(merged)} to review.")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
