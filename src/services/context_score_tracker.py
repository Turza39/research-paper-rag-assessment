"""
Service for tracking context scores and confidence in RAG responses.
Handles hallucination prevention and low-context handling.
"""
from typing import List, Dict, Tuple
import logging
from statistics import mean

logger = logging.getLogger(__name__)


class ContextScoreTracker:
    """Track and manage context relevance scores."""

    # Threshold constants
    HIGH_CONFIDENCE_THRESHOLD = 0.7
    MEDIUM_CONFIDENCE_THRESHOLD = 0.5
    LOW_CONFIDENCE_THRESHOLD = 0.3

    def __init__(self):
        """Initialize context tracker."""
        pass

    def calculate_context_score(
        self,
        retrieval_scores: List[float],
        query_coverage: float = 0.0,
        source_diversity: int = 0
    ) -> Tuple[float, str]:
        """
        Calculate overall context score for a query response.
        
        Args:
            retrieval_scores: List of similarity scores from vector search (0-1)
            query_coverage: Estimated coverage of query by retrieved content (0-1)
            source_diversity: Number of different papers referenced
        
        Returns:
            Tuple of (overall_score, confidence_level)
        """
        if not retrieval_scores:
            return 0.0, "very_low"
        
        # Base score from retrieval
        avg_retrieval_score = mean(retrieval_scores) if retrieval_scores else 0.0
        
        # Adjust for coverage
        coverage_bonus = query_coverage * 0.2  # Up to 0.2 bonus
        
        # Adjust for source diversity (penalize if too narrow)
        diversity_penalty = 0.0
        if source_diversity == 1:
            diversity_penalty = 0.1  # Small penalty for single source
        elif source_diversity == 0:
            diversity_penalty = 0.2  # Larger penalty for no sources
        
        # Calculate final score
        context_score = (avg_retrieval_score + coverage_bonus - diversity_penalty)
        context_score = max(0.0, min(1.0, context_score))  # Clamp to [0, 1]
        
        # Determine confidence level
        confidence_level = self._get_confidence_level(context_score)
        
        return context_score, confidence_level

    def _get_confidence_level(self, score: float) -> str:
        """Get confidence level from score."""
        if score >= self.HIGH_CONFIDENCE_THRESHOLD:
            return "high"
        elif score >= self.MEDIUM_CONFIDENCE_THRESHOLD:
            return "medium"
        elif score >= self.LOW_CONFIDENCE_THRESHOLD:
            return "low"
        else:
            return "very_low"

    def is_high_confidence(self, score: float) -> bool:
        """Check if score indicates high confidence."""
        return score >= self.HIGH_CONFIDENCE_THRESHOLD

    def is_low_confidence(self, score: float) -> bool:
        """Check if score indicates low confidence."""
        return score < self.LOW_CONFIDENCE_THRESHOLD

    def extract_retrieval_scores(self, results: List[Dict]) -> List[float]:
        """Extract similarity scores from search results."""
        return [r.get("score", 0.0) for r in results if r.get("score") is not None]

    def calculate_source_diversity(self, sources: List[str]) -> int:
        """Count unique sources."""
        return len(set(sources))

    def generate_low_confidence_warning(self, score: float) -> str:
        """Generate warning message for low-confidence responses."""
        if score < 0.2:
            return "⚠️ Very Low Confidence: I couldn't find strong relevant information. Please rephrase your question or provide more context."
        elif score < 0.4:
            return "⚠️ Low Confidence: The information I found may not fully address your question. Could you provide more details?"
        elif score < 0.6:
            return "ℹ️ Moderate Confidence: I found some relevant information, but it might not be comprehensive. Feel free to ask follow-up questions."
        else:
            return ""

    def calculate_hallucination_risk(
        self,
        context_score: float,
        retrieval_count: int,
        unique_sources: int
    ) -> Tuple[float, str]:
        """
        Calculate risk of hallucination based on context metrics.
        
        Returns:
            Tuple of (risk_score 0-1, risk_level)
        """
        # High risk if low context score
        base_risk = 1.0 - context_score
        
        # Lower risk if multiple sources
        source_diversity_bonus = min(0.3, unique_sources * 0.1)
        base_risk = max(0.0, base_risk - source_diversity_bonus)
        
        # Penalty if very few retrieval results
        if retrieval_count < 2:
            base_risk += 0.2
        elif retrieval_count < 5:
            base_risk += 0.1
        
        risk_score = max(0.0, min(1.0, base_risk))
        
        # Determine risk level
        if risk_score > 0.7:
            risk_level = "critical"
        elif risk_score > 0.5:
            risk_level = "high"
        elif risk_score > 0.3:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return risk_score, risk_level

    def should_ask_for_clarification(
        self,
        context_score: float,
        query_length: int,
        retrieval_count: int
    ) -> bool:
        """Determine if clarification should be requested."""
        # Ask for clarification if:
        # 1. Very low context score AND
        # 2. Few retrieval results AND
        # 3. Short query (likely ambiguous)
        conditions = [
            context_score < self.LOW_CONFIDENCE_THRESHOLD,
            retrieval_count < 3,
            query_length < 60
        ]
        return sum(conditions) >= 2

    def generate_hallucination_prevention_prompt(self, context_score: float) -> str:
        """Generate prompt to prevent hallucination based on context."""
        if context_score < 0.2:
            return (
                "⚠️ I don't have enough information from the papers to answer this question. "
                "Instead of guessing, I need you to provide more context or clarification. "
                "What specific aspect would you like me to focus on?"
            )
        elif context_score < 0.4:
            return (
                "ℹ️ I have limited information on this topic in the papers. "
                "I'll do my best to answer based on what I found, but please note that "
                "this might not be a complete answer. Would you like me to elaborate on any specific part?"
            )
        else:
            return ""
