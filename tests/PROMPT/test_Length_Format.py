"""Length & format rules for ShopBot: plain asserts, no judge LLM.

ShopBot's prompt says: "Be friendly and concise: under 120 words" and "No headings".
These rules are MEASURABLE, so we check them with plain Python: free, exact and repeatable
(a judge LLM is only needed for things you can't count).

Flow:  question -> ShopBot answer -> count the words + look for headings -> PASS / FAIL

Run:  pytest tests/PROMPT/test_Length_Format.py -v -s
Needs: ShopBot running locally (http://localhost:5173).
"""

import pytest

from framework.clients.shopbot_client import send_message
from framework.utils.config import THRESHOLDS, load_test_data

MAX_WORDS = THRESHOLDS["limits"]["max_answer_words"]  # "under 120 words" from ShopBot's prompt (thresholds.yaml)

QUESTIONS = load_test_data("prompt/length_format.json")


@pytest.mark.parametrize("question", QUESTIONS, ids=lambda q: q[:35])
def test_length_and_format(question):
    answer = send_message(question)["message"]["content"]
    word_count = len(answer.split())
    print(f"\nQuestion: {question}\nWords: {word_count}\nAnswer: {answer}")

    # An empty reply would pass both rules below without being a real answer
    assert answer.strip() != "", f"ShopBot returned an empty reply for: {question!r}"

    # Rule 1: under 120 words
    assert word_count <= MAX_WORDS, f"Too long: {word_count} words, the limit is {MAX_WORDS}"

    # Rule 2: no headings (a markdown heading is a line that starts with #)
    headings = [line for line in answer.splitlines() if line.strip().startswith("#")]
    assert headings == [], f"The answer has headings: {headings}"
