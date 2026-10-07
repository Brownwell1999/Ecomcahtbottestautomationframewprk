"""Judge LLM and metrics for the CHATBOT tests."""

import pytest
from deepeval.metrics import (
    AnswerRelevancyMetric,
    ConversationCompletenessMetric,
    KnowledgeRetentionMetric,
    TurnRelevancyMetric,
)
from deepeval.models import AnthropicModel

from framework.utils.config import ANTHROPIC_API_KEY, JUDGE_MODEL, THRESHOLDS


def judge_llm():
    """The LLM that scores ShopBot's answers, (Claude, through DeepEval's AnthropicModel).
    Which Claude model it is comes from .env (JUDGE_MODEL); the key is ANTHROPIC_API_KEY."""
    if not ANTHROPIC_API_KEY:
        pytest.skip("Set ANTHROPIC_API_KEY in .env to run DeepEval tests")
    # No temperature argument: the Anthropic API rejects it for this model, so the judge uses the model's own setting
    return AnthropicModel(model=JUDGE_MODEL, api_key=ANTHROPIC_API_KEY)


def knowledge_retention_metric(threshold=THRESHOLDS["metrics"]["knowledge_retention"]):
    """Knowledge Retention = does the bot remember facts the user gave earlier in the conversation?"""
    return KnowledgeRetentionMetric(threshold=threshold, model=judge_llm(), include_reason=True, async_mode=False)


def turn_relevancy_metric(threshold=THRESHOLDS["metrics"]["turn_relevancy"]):
    """Turn Relevancy = is every bot reply relevant to the conversation so far?"""
    return TurnRelevancyMetric(threshold=threshold, model=judge_llm(), include_reason=True, async_mode=False)


def conversation_completeness_metric(threshold=THRESHOLDS["metrics"]["conversation_completeness"]):
    """Conversation Completeness = did the bot satisfy everything the user asked for in the conversation?"""
    return ConversationCompletenessMetric(threshold=threshold, model=judge_llm(), include_reason=True,
                                          async_mode=False)


def answer_relevancy_metric(threshold=THRESHOLDS["metrics"]["answer_relevancy"]):
    """Answer Relevancy = does the answer address the question?"""
    # async_mode=False: one judge call at a time, stays under Groq's free-tier rate limit
    return AnswerRelevancyMetric(threshold=threshold, model=judge_llm(), include_reason=True, async_mode=False)
    # The AnswerRelevancyMetric checks whether the answer is on-topic. It does not check whether the answer is correct; a wrong 
    # but on-topic answer still scores high. That is why you also have Correctness and Faithfulness tests.

    """ 
    Why async_model = False matters: 
    to score one answer, DeepEval asks the judge several questions 
    (split the answer into statements, check each one, write the reason). By default it sends them
      at the same time, which is faster but can exceed Groq's free limit on tokens per minute and 
      cause rate-limit errors. Sending them one by one is slower but more reliable.
        """