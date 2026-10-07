"""Performance test for ShopBot: response time.

Performance = how FAST ShopBot answers (not how good the answer is).
We time one question with a stopwatch and check it is answered within a time budget.
No judge LLM, no DeepEval: a plain, deterministic check.

Flow:  start stopwatch -> ask ShopBot -> stop stopwatch -> answer not empty + time <= budget -> PASS / FAIL

Run:  pytest tests/LLM/test_Performance.py -v -s
Needs: ShopBot running locally (http://localhost:5173).
"""

import time

import pytest

from framework.clients.shopbot_client import send_message
from framework.utils.config import THRESHOLDS

MAX_SECONDS = THRESHOLDS["limits"]["quick_response_time_seconds"]  # time budget (SLA) for one answer (thresholds.yaml)


@pytest.mark.performance
def test_response_time():
    question = "What is your return policy for electronics?"

    # 1. Start the stopwatch
    start = time.perf_counter()

    # 2. Ask ShopBot
    answer = send_message(question)["message"]["content"]

    # 3. Stop the stopwatch: seconds taken = now - start
    elapsed = time.perf_counter() - start
    print(f"\nQuestion: {question}\nAnswer: {answer}\nResponse time: {elapsed:.2f} s (budget {MAX_SECONDS} s)")

    # 4. It really answered (a fast empty reply is not a pass)
    assert answer.strip() != "", "ShopBot returned an empty answer"

    # 5. It answered within the time budget
    assert elapsed <= MAX_SECONDS, f"ShopBot took {elapsed:.2f} s, budget is {MAX_SECONDS} s"
