"""API reliability / error handling: ShopBot handles bad requests and timeouts WITHOUT crashing
and without returning broken responses.

What "handled well" means:
  - no server crash: never HTTP 500, and the service is still healthy afterwards
  - a VALID error response: JSON with an "errors" list, a readable message and an error code
  - timeouts are raised cleanly on the client (the test doesn't hang forever)
No judge LLM, no DeepEval: httpx + pytest + plain asserts.

These tests need the RAW HTTP response (status code, errors), so they call ShopBot with httpx
directly instead of send_message(), which stops at the first error.

Run:  pytest tests/PERFORMANCE/test_reliability_and_error_handling.py -v -s
Needs: ShopBot running locally (http://localhost:5173).
"""

import httpx
import pytest

from framework.clients.shopbot_client import SEND_MESSAGE
from framework.utils.config import GRAPHQL_URL


def send_raw(message_input, timeout=60):
    """Send one chat message to ShopBot and return the raw HTTP response (no error checking)."""
    body = {"query": SEND_MESSAGE, "variables": {"input": message_input}}
    return httpx.post(GRAPHQL_URL, json=body, timeout=timeout)


def check_clear_error(response):
    """A bad input must give a clear error, not a crash and not a half-made answer."""
    body = response.json()
    first_error = body["errors"][0]
    print()
    print("HTTP status:", response.status_code)
    print("Error message:", first_error["message"])
    print("Error code:", first_error["extensions"]["code"])

    assert response.status_code == 200                              # GraphQL: errors come in the body
    assert body["data"] is None                                     # no half-made answer
    assert first_error["message"] != ""                             # a readable message
    assert first_error["extensions"]["code"] == "BAD_USER_INPUT"    # a machine-readable code


# ---------- 1. Bad input -> clear error, not a crash ----------
@pytest.mark.performance
def test_empty_message_returns_clear_error():
    response = send_raw({"text": "   "})
    check_clear_error(response)


@pytest.mark.performance
def test_too_long_message_returns_clear_error():
    too_long = "a" * 2001   # ShopBot's limit is 2000 characters
    response = send_raw({"text": too_long})
    check_clear_error(response)


@pytest.mark.performance
def test_invalid_conversation_id_returns_clear_error():
    response = send_raw({"text": "hi", "conversationId": "not-a-valid-id!!"})
    check_clear_error(response)


# ---------- 2. Broken requests -> rejected, not a crash ----------
@pytest.mark.performance
def test_invalid_graphql_query_is_rejected():
    # Ask for a field that doesn't exist
    response = httpx.post(GRAPHQL_URL, json={"query": "{ notAField }"}, timeout=30)
    error_message = response.json()["errors"][0]["message"]
    print()
    print("HTTP status:", response.status_code)
    print("Error message:", error_message)

    assert response.status_code == 200
    assert "Cannot query field" in error_message


@pytest.mark.performance
def test_malformed_json_is_rejected():
    # Send text that is not valid JSON
    response = httpx.post(GRAPHQL_URL, content=b"{broken json",
                          headers={"Content-Type": "application/json"}, timeout=30)
    print()
    print("HTTP status:", response.status_code)

    assert response.status_code == 400   # client error (4xx), NOT a server crash (500)


# ---------- 3. Timeout -> handled cleanly on the client ----------
@pytest.mark.performance
def test_timeout_is_raised_cleanly():
    # A 1 ms timeout is far too short for an LLM answer, so httpx must raise a timeout error.
    # pytest.raises = the test PASSES only if that error is raised.
    with pytest.raises(httpx.TimeoutException):
        send_raw({"text": "What is your return policy for electronics?"}, timeout=0.001)


# ---------- 4. After all the bad requests, ShopBot still works ----------
@pytest.mark.performance
def test_service_still_healthy_after_errors():
    # Hit ShopBot with the bad requests again
    send_raw({"text": "   "})
    send_raw({"text": "a" * 2001})
    send_raw({"text": "hi", "conversationId": "not-a-valid-id!!"})

    # The health check still says ok
    health = httpx.post(GRAPHQL_URL, json={"query": "{ health }"}, timeout=30).json()
    print()
    print("Health:", health)
    assert health["data"]["health"] == "ok"

    # A real question still gets a real answer
    reply = send_raw({"text": "What warranty do headphones have?"}).json()
    answer = reply["data"]["sendMessage"]["message"]["content"]
    print("Real answer:", answer[:80])
    assert answer.strip() != ""


# Notes:
#   - GraphQL returns HTTP 200 even for errors -> always check body["errors"], not just the status.
#   - 4xx = the client sent something wrong; 5xx = the server broke. Bad input must never give 5xx.
