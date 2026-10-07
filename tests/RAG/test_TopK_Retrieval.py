"""Top-K retrieval test for ShopBot's RAG (no judge LLM, so it is fast and gives the same result every time).

Top-K retrieval = for a question, the retriever returns its K best-matching chunks.
We check that the RIGHT chunk is among them and ranked high.

Run:  pytest tests/RAG/test_TopK_Retrieval.py -v -s
Needs: ShopBot running locally (http://localhost:5173).
"""

from framework.clients.shopbot_client import retrieve
from framework.utils.config import THRESHOLDS, load_test_data

TOP_K = 4  # how many chunks the retriever returns
MAX_RANK = THRESHOLDS["limits"]["top_k_max_rank"]  # the right chunk must be at this position or better (thresholds.yaml)

# Each case: a question and the chunk that holds its answer (chunk_id = "<file>#<chunk number>")
CASES = load_test_data("rag/top_k_retrieval.json")


def test_top_k_retrieval():
    for case in CASES:
        question = case["question"]
        expected_chunk = case["expected_chunk_id"]

        # Ask the retriever: it returns a list of chunks, best match first
        chunks = retrieve(question, k=TOP_K)
        chunk_ids = [chunk["chunk_id"] for chunk in chunks]
        scores = [chunk["score"] for chunk in chunks]
        print(f"\nQuestion: {question}\nExpected chunk: {expected_chunk}\nFound: {chunk_ids}")

        # 1. The retriever returns exactly K chunks
        assert len(chunks) == TOP_K, f"{question!r}: expected {TOP_K} chunks, got {len(chunks)}"

        # 2. The right chunk is somewhere in the top K
        assert expected_chunk in chunk_ids, f"{question!r}: {expected_chunk} not found in {chunk_ids}"

        # 3. The right chunk is near the top (position 1 = best)
        position = chunk_ids.index(expected_chunk) + 1
        assert position <= MAX_RANK, f"{question!r}: {expected_chunk} is at position {position}, expected top {MAX_RANK}"

        # 4. The scores go from highest to lowest
        assert scores == sorted(scores, reverse=True), f"{question!r}: scores are not sorted: {scores}"
