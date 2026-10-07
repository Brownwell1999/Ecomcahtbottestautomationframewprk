"""Response time (latency) tests for ShopBot.

Performance = how FAST ShopBot answers (not how good the answer is).
No judge LLM, no DeepEval: a stopwatch (time.perf_counter) and plain asserts.

  Test 1: one question        -> answered within the time budget?
  Test 2: same question 5x    -> p95 (almost-worst case) within the time budget?

Flow:  warm-up call -> start stopwatch -> ask ShopBot -> stop stopwatch -> check answer + time

Run:  pytest tests/PERFORMANCE/test_response_time.py -v -s
Needs: ShopBot running locally (http://localhost:5173).
"""

import math
import time

import pytest

from framework.clients.shopbot_client import send_message
from framework.utils.config import THRESHOLDS

QUESTION = "What is your return policy for electronics?"
RUNS = 5           # how many timed requests for the p95 test
MAX_SECONDS = THRESHOLDS["limits"]["response_time_seconds"]   # time budget for one answer (thresholds.yaml)


def ask_and_time(question):
    """Ask ShopBot one question; return the answer and the seconds it took."""
    start = time.perf_counter()                 # start the stopwatch
    answer = send_message(question)["message"]["content"]
    seconds = time.perf_counter() - start       # stop the stopwatch
    return answer, seconds


@pytest.mark.performance
def test_single_response_time():
    # Warm-up (not measured): the first call after start-up is often slower
    ask_and_time(QUESTION)

    answer, seconds = ask_and_time(QUESTION)
    print()
    print("Question:", QUESTION)
    print("Response time:", round(seconds, 2), "seconds. Budget:", MAX_SECONDS, "seconds")

    assert answer.strip() != "", "ShopBot returned an empty answer"
    assert seconds <= MAX_SECONDS, f"ShopBot took {round(seconds, 2)} seconds, the budget is {MAX_SECONDS}"


@pytest.mark.performance
def test_p95_response_time():
    # Warm-up (not measured)
    ask_and_time(QUESTION)

    # 1. Ask the same question RUNS times and keep every response time
    times = []
    for run in range(1, RUNS + 1):
        answer, seconds = ask_and_time(QUESTION)
        print("Run", run, ":", round(seconds, 2), "seconds")
        assert answer.strip() != "", f"Run {run}: ShopBot returned an empty answer"
        times.append(seconds)

    # 2. Average = the typical speed
    average = sum(times) / len(times)

    # 3. p95 = 95% of the answers were this fast or faster.
    #    Sort the times from fastest to slowest and take the one at the 95% position
    #    (with 5 runs that is position 5, the slowest run).
    times.sort()
    position = math.ceil(0.95 * len(times))
    p95 = times[position - 1]   # lists count from 0, so position 5 is index 4

    print("Average:", round(average, 2), "seconds")
    print("p95:    ", round(p95, 2), "seconds. Budget:", MAX_SECONDS, "seconds")

    # 4. PASS if even the (almost) slowest answer is within the budget
    assert p95 <= MAX_SECONDS, f"p95 is {round(p95, 2)} seconds, the budget is {MAX_SECONDS}"


# Why p95 and not the average?
#   LLM response times vary a lot. An average of 3 s can hide one 20 s answer that a real
#   user waited for. p95 = "95% of users got an answer at least this fast", so we assert on it.
# Why a warm-up call?
#   The first request after start-up is slower (connections, model loading). Leaving it out
#   measures the normal speed users get.
