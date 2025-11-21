"""
Service for classifying queries and detecting context types.
Handles keyword-based and global queries for research papers.
"""
import re
from typing import Dict, List, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class QueryType(str, Enum):
    """Query type classification."""
    SECTION_SPECIFIC = "section_specific"      # Asking about specific paper sections
    GLOBAL_QUERY = "global_query"              # Summary, overview, translate, etc.
    CONTEXT_SPECIFIC = "context_specific"      # General question within context
    OUT_OF_CONTEXT = "out_of_context"          # Greeting, casual talk
    CLARIFICATION_NEEDED = "clarification_needed"  # Ambiguous or unclear


class QueryClassifier:
    """Classify and analyze user queries for context-aware responses."""

    # Common paper sections to detect
    PAPER_SECTIONS = {
        "abstract": ["abstract", "summary", "overview"],
        "introduction": ["introduction", "intro", "background", "related work"],
        "methodology": ["methodology", "method", "approach", "framework", "architecture"],
        "results": ["results", "result", "findings", "experiments", "experimental", "evaluation"],
        "conclusion": ["conclusion", "conclusions", "summary", "future work", "limitations"],
        "references": ["references", "citations", "bibliography"],
        "discussion": ["discussion", "analysis", "implications"],
        "future_work": ["future work", "future research", "future directions"]
    }

    # Global query keywords (apply across all papers)
    GLOBAL_KEYWORDS = {
        "summary": ["summary", "summarize", "summarization", "summed up", "tl;dr"],
        "overview": ["overview", "overview", "big picture", "high level"],
        "translate": ["translate", "translation", "convert", "rephrase"],
        "rewrite": ["rewrite", "rewriting", "paraphrase", "simplify"],
        "bullet": ["bullet", "bullets", "points", "list"],
        "compare": ["compare", "comparison", "vs", "versus", "difference"],
        "explain": ["explain", "explanation", "clarify", "elaborate"],
    }

    # Out-of-context keywords (greetings, casual talk)
    OUT_OF_CONTEXT_KEYWORDS = {
        "greeting": ["hi", "hello", "hey", "greetings", "howdy"],
        "casual": ["how are you", "how's it going", "what's up", "thanks", "thank you"],
        "meta": ["what can you do", "help", "what is this", "who are you", "tell me about yourself"],
    }

    def classify(self, query: str) -> Dict:
        """
        Classify a query and extract relevant metadata.
        
        Returns:
            Dict with keys:
            - query_type: QueryType enum value
            - detected_section: str or None (if section_specific)
            - is_global: bool (if global query)
            - global_operation: str or None (what kind of global operation)
            - confidence: float (0-1)
            - requires_clarification: bool
        """
        query_lower = query.lower().strip()
        
        # Check for out-of-context queries first
        out_of_context_result = self._check_out_of_context(query_lower)
        if out_of_context_result["match"]:
            return {
                "query_type": QueryType.OUT_OF_CONTEXT,
                "category": out_of_context_result["category"],
                "confidence": out_of_context_result["confidence"],
                "detected_section": None,
                "is_global": False,
                "global_operation": None,
                "requires_clarification": False,
            }
        
        # Check for global queries
        global_result = self._check_global_query(query_lower)
        if global_result["match"]:
            return {
                "query_type": QueryType.GLOBAL_QUERY,
                "global_operation": global_result["operation"],
                "confidence": global_result["confidence"],
                "detected_section": None,
                "is_global": True,
                "requires_clarification": False,
            }
        
        # Check for section-specific queries
        section_result = self._check_section_specific(query_lower)
        if section_result["match"]:
            return {
                "query_type": QueryType.SECTION_SPECIFIC,
                "detected_section": section_result["section"],
                "confidence": section_result["confidence"],
                "is_global": False,
                "global_operation": None,
                "requires_clarification": False,
            }
        
        # Default to context_specific
        return {
            "query_type": QueryType.CONTEXT_SPECIFIC,
            "detected_section": None,
            "is_global": False,
            "global_operation": None,
            "confidence": 0.7,
            "requires_clarification": False,
        }

    def _check_section_specific(self, query_lower: str) -> Dict:
        """Check if query targets specific paper sections."""
        matches = []
        
        for section_name, keywords in self.PAPER_SECTIONS.items():
            for keyword in keywords:
                # Match whole words only
                if re.search(r'\b' + re.escape(keyword) + r'\b', query_lower):
                    matches.append((section_name, keyword))
        
        if matches:
            # Return the most frequently matched section
            best_section = max(set([m[0] for m in matches]))
            confidence = min(1.0, len(matches) * 0.3)  # Increase confidence with more matches
            return {
                "match": True,
                "section": best_section,
                "confidence": confidence
            }
        
        return {"match": False, "section": None, "confidence": 0.0}

    def _check_global_query(self, query_lower: str) -> Dict:
        """Check if query is a global operation (summary, translate, etc.)."""
        matches = []
        
        for operation, keywords in self.GLOBAL_KEYWORDS.items():
            for keyword in keywords:
                if re.search(r'\b' + re.escape(keyword) + r'\b', query_lower):
                    matches.append(operation)
        
        if matches:
            best_operation = matches[0]  # Return first matched operation
            confidence = min(1.0, len(set(matches)) * 0.4)
            return {
                "match": True,
                "operation": best_operation,
                "confidence": confidence
            }
        
        return {"match": False, "operation": None, "confidence": 0.0}

    def _check_out_of_context(self, query_lower: str) -> Dict:
        """Check if query is out of research context (greeting, casual)."""
        matches = []
        category = None
        
        for cat, keywords in self.OUT_OF_CONTEXT_KEYWORDS.items():
            for keyword in keywords:
                if re.search(r'\b' + re.escape(keyword) + r'\b', query_lower):
                    matches.append(cat)
                    category = cat
        
        if matches:
            confidence = min(1.0, len(matches) * 0.3)
            return {
                "match": True,
                "category": category,
                "confidence": confidence
            }
        
        return {"match": False, "category": None, "confidence": 0.0}

    def extract_context_keywords(self, query: str) -> List[str]:
        """Extract potential paper section keywords from query."""
        query_lower = query.lower()
        keywords = []
        
        for section_name, section_keywords in self.PAPER_SECTIONS.items():
            for keyword in section_keywords:
                if re.search(r'\b' + re.escape(keyword) + r'\b', query_lower):
                    keywords.append(keyword)
        
        return list(set(keywords))  # Remove duplicates

    def should_ask_clarification(self, context_score: float, query_length: int) -> bool:
        """Determine if clarification should be asked based on context score."""
        # Ask for clarification if:
        # - Very low context score AND
        # - Query is short (likely ambiguous)
        return context_score < 0.3 and query_length < 50

    def generate_clarification_prompt(self, detected_issue: str = "low_context") -> str:
        """Generate a clarification prompt for the user."""
        prompts = {
            "low_context": "I couldn't find enough relevant information in the papers. Could you provide more details about what you're looking for? For example, which paper or which section?",
            "ambiguous": "Your query seems a bit unclear. Could you be more specific? You can ask about sections like abstract, introduction, methodology, results, or conclusion.",
            "no_context": "This question doesn't seem to be about the research papers. I'm here to help you understand the content of the uploaded papers. Feel free to ask questions about their methodology, results, conclusions, or other sections!",
        }
        return prompts.get(detected_issue, prompts["low_context"])

    def generate_greeting_response(self, category: str) -> str:
        """Generate appropriate response for out-of-context queries."""
        responses = {
            "greeting": "Hi! I'm a research assistant here to help you understand the uploaded research papers. You can ask me about specific sections, request summaries, or get explanations about concepts. What would you like to know?",
            "casual": "I'm doing well, thanks for asking! I'm ready to help you explore the research papers. What would you like to know about them?",
            "meta": "I'm a research paper assistant powered by RAG (Retrieval Augmented Generation). I can help you:\n- Find information in specific sections (abstract, methodology, results, etc.)\n- Summarize papers or specific sections\n- Compare content across papers\n- Explain complex concepts\n\nJust upload your research papers and ask away!",
        }
        return responses.get(category, "How can I help you with your research papers?")
