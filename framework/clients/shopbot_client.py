"""Functions for talking to the ShopBot GraphQL API: the one place tests call the chatbot."""

import httpx

from framework.utils.config import GRAPHQL_URL

# ShopBot's retriever and NLU on their own (dev/test only), reached on the same host as the GraphQL API
RETRIEVE_URL = GRAPHQL_URL.removesuffix("/graphql") + "/api/chat/eval/retrieve"
NLU_URL = GRAPHQL_URL.removesuffix("/graphql") + "/api/chat/eval/nlu"

LOGIN = """
mutation Login($email: String!, $password: String!) {
  login(email: $email, password: $password) { token }
}"""

# conversationId: send it back to stay in the same conversation (multi-turn)
# debug: what ShopBot did to answer (only returned in dev/test) - RAG chunks, agent tool calls
SEND_MESSAGE = """
mutation SendMessage($input: SendMessageInput!) {
  sendMessage(input: $input) {
    conversationId
    message { content }
    debug {
      promptVersion
      retrievalContext
      toolCalls { name args output }
      llmCalls { model }
    }
  }
}"""

# What ShopBot reported about itself in the replies of this run (filled in by send_message).
# The baseline comparison uses it to label a run with the prompt version and the models that were tested.
SEEN = {"prompt_version": None, "models": set()}


def send_message(text, conversation_id=None, agent_mode=False, token=None, timeout=60):
    """Send one message to ShopBot and return its reply:
    {"conversationId": ..., "message": {"content": ...}, "debug": {...}}.

    conversation_id=None starts a new conversation; pass the returned conversationId to continue it.
    agent_mode=True lets the LLM choose tools. token (from login) sends the message as that customer."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    variables = {"input": {"text": text, "conversationId": conversation_id, "agentMode": agent_mode}}
    response = httpx.post(GRAPHQL_URL, json={"query": SEND_MESSAGE, "variables": variables},
                          headers=headers, timeout=timeout)
    body = response.json()
    # GraphQL errors come back as HTTP 200 + "errors", so check the body, not only the status
    assert "errors" not in body, f"ShopBot returned errors: {body['errors']}" #A GraphQL server can return HTTP 200 OK while reporting an error in the JSON response. This assertion catches that case.
    reply = body["data"]["sendMessage"]

    debug = reply["debug"]  # only returned in dev/test
    if debug:
        SEEN["prompt_version"] = debug["promptVersion"]
        SEEN["models"].update(call["model"] for call in debug["llmCalls"])
    return reply


def login(email, password):
    """Sign in as a demo customer and return the token."""
    response = httpx.post(GRAPHQL_URL, json={"query": LOGIN, "variables": {"email": email, "password": password}},
                          timeout=60)
    body = response.json()
    assert "errors" not in body, f"Login failed: {body['errors']}"
    return body["data"]["login"]["token"]


def retrieve(question, k=4, timeout=60):
    """Ask ShopBot's retriever alone (no LLM answer): returns its top-k chunks, best first.
    Each chunk is a dict with chunk_id (e.g. "return_policy.md#0"), score, used, section, content..."""
    response = httpx.post(RETRIEVE_URL, json={"query": question, "k": k}, timeout=timeout)
    response.raise_for_status()
    return response.json()


def nlu(message, timeout=60):
    """Ask ShopBot's NLU step alone (no answer is written): returns its JSON result
    {"intent": ..., "confidence": ..., "entities": {...}, "source": ...}."""
    response = httpx.post(NLU_URL, json={"message": message}, timeout=timeout)
    response.raise_for_status()
    return response.json()
