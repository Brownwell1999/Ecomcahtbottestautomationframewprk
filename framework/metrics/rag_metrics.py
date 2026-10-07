"""RAG metrics: judge the retriever (the "R") and the generator (the "G") of ShopBot's RAG."""

from deepeval.metrics import (
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    ContextualRelevancyMetric,
    ConversationalGEval,
    FaithfulnessMetric,
    TurnContextualRelevancyMetric,
    TurnFaithfulnessMetric,
)
from deepeval.test_case import MultiTurnParams

from framework.metrics.chatbot_metrics import judge_llm
from framework.utils.config import THRESHOLDS

# async_mode=False on all of them: one judge call at a time, stays under Groq's free-tier rate limit


def contextual_relevancy_metric(threshold=THRESHOLDS["metrics"]["contextual_relevancy"]):
    """Is the retrieved text relevant to the question? 0.5 = DeepEval's default (chunks always carry extra text)."""
    return ContextualRelevancyMetric(threshold=threshold, model=judge_llm(), include_reason=True, async_mode=False)


def contextual_recall_metric(threshold=THRESHOLDS["metrics"]["contextual_recall"]):
    """Did retrieval find everything needed for the correct (expected) answer?"""
    return ContextualRecallMetric(threshold=threshold, model=judge_llm(), include_reason=True, async_mode=False)


def contextual_precision_metric(threshold=THRESHOLDS["metrics"]["contextual_precision"]):
    """Are the useful chunks ranked above the useless ones?"""
    return ContextualPrecisionMetric(threshold=threshold, model=judge_llm(), include_reason=True, async_mode=False)


def faithfulness_metric(threshold=THRESHOLDS["metrics"]["faithfulness"]):
    """Is every claim in the answer backed by the retrieved chunks (no hallucination)?"""
    return FaithfulnessMetric(threshold=threshold, model=judge_llm(), include_reason=True, async_mode=False)


def conversational_correctness_metric(threshold=THRESHOLDS["metrics"]["conversational_correctness"]):
    """Custom multi-turn metric (ConversationalGEval): the criteria sentence IS the metric.
    The judge reads every turn (role + content) and scores the WHOLE conversation 0..1."""
    return ConversationalGEval(
        name="Correctness",
        criteria=(
            "Did the chatbot fully resolve the customer's questions across the conversation? "
            "It should give accurate, consistent answers and remember what it said earlier."
        ),
        model=judge_llm(),
        threshold=threshold,
        evaluation_params=[MultiTurnParams.ROLE, MultiTurnParams.CONTENT],  # what the judge may see of each turn
        async_mode=False,
    )


def turn_faithfulness_metric(threshold=THRESHOLDS["metrics"]["turn_faithfulness"]):
    """Multi-turn Faithfulness: in every turn, is the reply backed by the chunks retrieved for that turn?"""
    return TurnFaithfulnessMetric(threshold=threshold, model=judge_llm(), include_reason=True, async_mode=False)


def turn_contextual_relevancy_metric(threshold=THRESHOLDS["metrics"]["turn_contextual_relevancy"]):
    """Multi-turn Contextual Relevancy: in every turn, are the retrieved chunks relevant to what the user asked?
    0.5 = DeepEval's default (chunks always carry extra text)."""
    return TurnContextualRelevancyMetric(threshold=threshold, model=judge_llm(), include_reason=True,
                                         async_mode=False)
