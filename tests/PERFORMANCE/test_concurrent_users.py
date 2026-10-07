"""Concurrent users / load: ShopBot stays functional when several users send requests at the SAME time.

We simulate several people chatting at once with Python's ThreadPoolExecutor (each thread = one user,
each with their own question and their own new conversation), then check that EVERY user got a
successful answer. Times are printed so you can see how load slows things down.
No judge LLM, no DeepEval: plain asserts.

Flow:  start all users together -> wait for all -> check each one: no error, answer not empty

Run:  pytest tests/PERFORMANCE/test_concurrent_users.py -v -s
Needs: ShopBot running locally (http://localhost:5173).
"""

import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from framework.clients.shopbot_client import send_message
from framework.utils.config import load_test_data

# One question per simulated user (different questions = more realistic load)
QUESTIONS = load_test_data("performance/concurrent_users.json")
USERS = len(QUESTIONS)   # 5 users at the same time
TIMEOUT_SECONDS = 120    # a single request may not hang longer than this


def one_user(question):
    """What ONE user does: send a question; return the answer (or the error) and how long it took."""
    start = time.perf_counter()
    try:
        answer = send_message(question, timeout=TIMEOUT_SECONDS)["message"]["content"]
        error = None
    except Exception as problem:  # HTTP error, GraphQL error (e.g. RATE_LIMITED) or timeout
        answer = ""
        error = str(problem)
    seconds = time.perf_counter() - start
    return {"question": question, "answer": answer, "error": error, "seconds": seconds}


@pytest.mark.performance
def test_concurrent_users():
    # 1. Start all users at the same time and wait until every one has finished.
    #    pool.map() runs one_user() once per question, each in its own thread.
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=USERS) as pool:
        results = list(pool.map(one_user, QUESTIONS))
    total_seconds = time.perf_counter() - start

    # 2. Show what each user got
    for result in results:
        print()
        print("Question:", result["question"])
        print("Seconds: ", round(result["seconds"], 2))
        if result["error"] is None:
            print("Answer:  ", result["answer"][:80])   # first 80 characters are enough to see it answered
        else:
            print("Error:   ", result["error"])
    print()
    print(USERS, "users served in", round(total_seconds, 2), "seconds in total")

    # 3. Every user must get a working answer
    for result in results:
        question = result["question"]
        error = result["error"]
        answer = result["answer"]

        assert error is None, f"Request failed for '{question}': {error}"
        assert answer.strip() != "", f"Empty answer for '{question}'"



"""

Concurrent user testing checks whether ShopBot can handle multiple users 
sending requests at approximately the same time while returning valid responses.

# ThreadPoolExecutor: runs multiple functions concurrently using a pool of threads.
Why threads? Your test spends much of its time waiting for HTTP responses. 
Threads allow other requests to be in progress while one request is waiting.

"""