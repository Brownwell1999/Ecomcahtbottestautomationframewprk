"""API -> send question -> receive response -> response is not empty.

Run:  pytest tests/CHATBOT/test_receive_response.py -v -s     (or: pytest -m smoke -v -s)
Needs ShopBot running locally (http://localhost:5173).
"""

import pytest

from framework.clients.shopbot_client import send_message


@pytest.mark.smoke
def test_receive_response():
    question = "What is your return policy for electronics?"

    # Send question -> receive response
    reply = send_message(question)
    actual_response = reply["message"]["content"]
    print(f"\nQuestion: {question}\nResponse: {actual_response}")

    

    # The response is not empty
    response_text = actual_response.strip()
    assert response_text != "", f"Chatbot returned an empty response for question: {question!r}"

""" .strip() removes spaces and newlines from both ends. Without it, a reply of "   " (only spaces) would count as "not empty" and the test would wrongly pass.
    So if ShopBot ever returned a blank reply, you would see:
    AssertionError: Chatbot returned an empty response for question: 'What is your return policy for electronics?'
    !r inserts it in its "repr" form instead, which adds quotes and makes hidden characters visible. """