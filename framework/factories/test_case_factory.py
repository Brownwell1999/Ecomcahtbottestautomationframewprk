"""Build DeepEval test cases from real ShopBot conversations."""

from deepeval.test_case import ConversationalTestCase, LLMTestCase, ToolCall, Turn

from framework.clients.shopbot_client import send_message


def rag_test_case(question, expected_output):
    """Ask ShopBot one question; return the answer + the chunks its retriever found as a test case."""
    reply = send_message(question)
    actual_response = reply["message"]["content"]
    retrieval_context = reply["debug"]["retrievalContext"]  # debug is only returned in dev/test
    print(f"\nQuestion: {question}\nActual response: {actual_response}")
    for number, chunk in enumerate(retrieval_context, start=1):
        print(f"\n--- Retrieved chunk {number} ---\n{chunk}")
    return LLMTestCase(input=question, actual_output=actual_response,
                       expected_output=expected_output, retrieval_context=retrieval_context)


def agent_test_case(question, expected_tools=None, token=None):
    """Ask ShopBot in AGENT mode (the LLM chooses its own tools); return what the agent DID as a test case:
    the tools it called (name, arguments, output) and its final answer.
    expected_tools = tool names we expect, in order (only needed by the Tool Correctness metric)."""
    reply = send_message(question, agent_mode=True, token=token, timeout=180)  # agent mode can be slow
    answer = reply["message"]["content"]
    calls = reply["debug"]["toolCalls"]
    print(f"\nQuestion: {question}\nCalled tools: {[call['name'] for call in calls]}\nAnswer: {answer}")
    return LLMTestCase(
        input=question,
        actual_output=answer,
        tools_called=[ToolCall(name=c["name"], input_parameters=c["args"], output=c["output"]) for c in calls],
        expected_tools=[ToolCall(name=name) for name in expected_tools] if expected_tools else None,
    )


def run_conversation(questions, with_chunks=False):
    """Send all questions in ONE conversation; return it as a multi-turn DeepEval test case.
    with_chunks=True also keeps the chunks ShopBot retrieved for each reply (for the RAG turn metrics)."""
    turns = [] # list of objects
    conversation_id = None  # None -> ShopBot starts a new conversation
    for question in questions:
        reply = send_message(question, conversation_id)
        conversation_id = reply["conversationId"]  # send it back next time -> same conversation
        actual_response = reply["message"]["content"]
        chunks = reply["debug"]["retrievalContext"] if with_chunks else None
        print(f"\nUser: {question}\nShopBot: {actual_response}")
        if with_chunks:
            print(f"Retrieved chunks: {len(chunks)}")

        turns.append(Turn(role="user", content=question))
        turns.append(Turn(role="assistant", content=actual_response, retrieval_context=chunks))
    return ConversationalTestCase(turns=turns)

"""

Why a list and not a dictionary ?
A conversation is an ordered sequence, and the same speaker appears many times. 
A dictionary needs unique keys, so {"user": ..., "assistant": ...} could hold only
one message per side and would lose both the order and the earlier messages.

"""