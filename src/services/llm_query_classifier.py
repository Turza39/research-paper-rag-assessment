"""
LLM-based query classifier for more accurate global vs local query detection.
Uses Gemini API to determine if a query should be applied to:
- GLOBAL: All papers combined (summary, compare, translate, rewrite, etc.)
- LOCAL: Specific paper sections (extract specific information, methodology, results, etc.)
"""

import logging
from typing import Dict, Optional
import google.generativeai as genai
from enum import Enum

logger = logging.getLogger(__name__)


class QueryScope(str, Enum):
    """Query scope classification."""
    GLOBAL = "global"          # Apply across all papers
    LOCAL = "local"            # Apply to specific sections/papers
    OUT_OF_CONTEXT = "out_of_context"  # Greetings, meta questions


class LLMQueryClassifier:
    """Classify queries using LLM for accurate scope detection."""

    CLASSIFICATION_PROMPT = """Analyze the following research paper query and determine its scope.

Query: "{query}"

Respond with ONLY one of these formats:
1. For queries that need GLOBAL operation (across all papers):
   SCOPE: global
   OPERATION: [summary/translate/rewrite/compare/overview/bullet]
   REASON: [brief reason]

2. For queries about SPECIFIC content (local/section-specific):
   SCOPE: local
   REASON: [brief reason]

3. For casual/non-academic queries:
   SCOPE: out_of_context
   REASON: [brief reason]

Examples:
- "Summarize all papers" → SCOPE: global, OPERATION: summary
- "Compare methodology of all papers" → SCOPE: global, OPERATION: compare
- "What is the abstract of paper 1?" → SCOPE: local
- "Explain the results section" → SCOPE: local
- "Hello, how are you?" → SCOPE: out_of_context
- "What machine learning algorithms were used?" → SCOPE: local

Determine the scope accurately:"""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize LLM query classifier."""
        if api_key:
            genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")
        logger.info("✅ LLM Query Classifier initialized")

    def classify(self, query: str) -> Dict:
        """
        Classify query scope using LLM.
        
        Args:
            query: User's research query
            
        Returns:
            Dict with:
            - scope: QueryScope (global/local/out_of_context)
            - operation: str or None (for global: summary/translate/rewrite/compare/overview/bullet)
            - reason: str (classification reasoning)
            - confidence: float (0-1)
            - full_context: Optional (full PDF context or Qdrant retrieval hint)
        """
        try:
            prompt = self.CLASSIFICATION_PROMPT.format(query=query)
            
            logger.debug(f"🤖 Sending query to LLM for classification: '{query}'")
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,  # Low temperature for consistent classification
                    max_output_tokens=200
                )
            )
            
            result_text = response.text.strip()
            logger.debug(f"📝 LLM Response:\n{result_text}")
            
            # Parse response
            parsed = self._parse_llm_response(result_text)
            
            return {
                "scope": parsed["scope"],
                "operation": parsed.get("operation"),
                "reason": parsed.get("reason", ""),
                "confidence": parsed.get("confidence", 0.9),
                "is_global": parsed["scope"] == QueryScope.GLOBAL,
                "is_local": parsed["scope"] == QueryScope.LOCAL,
                "is_out_of_context": parsed["scope"] == QueryScope.OUT_OF_CONTEXT,
            }
            
        except Exception as e:
            logger.error(f"❌ LLM classification failed: {str(e)}")
            # Fallback to conservative classification
            return self._fallback_classification(query)

    def _parse_llm_response(self, response_text: str) -> Dict:
        """Parse LLM response into structured format."""
        result = {
            "scope": QueryScope.LOCAL,  # Default to local
            "operation": None,
            "reason": "",
            "confidence": 0.9
        }
        
        lines = response_text.lower().split("\n")
        
        for line in lines:
            if "scope:" in line:
                if "global" in line:
                    result["scope"] = QueryScope.GLOBAL
                elif "local" in line:
                    result["scope"] = QueryScope.LOCAL
                elif "out_of_context" in line:
                    result["scope"] = QueryScope.OUT_OF_CONTEXT
                    
            elif "operation:" in line:
                # Extract operation type
                line_content = line.split("operation:")[1].strip()
                operations = ["summary", "translate", "rewrite", "compare", "overview", "bullet"]
                for op in operations:
                    if op in line_content:
                        result["operation"] = op
                        break
                        
            elif "reason:" in line:
                result["reason"] = line.split("reason:")[1].strip()
        
        return result

    def _fallback_classification(self, query: str) -> Dict:
        """Fallback classification using keyword matching if LLM fails."""
        query_lower = query.lower()
        
        # Out-of-context keywords
        out_of_context_keywords = [
            "hi", "hello", "hey", "how are you", "thanks", "thank you",
            "who are you", "what can you do", "help me"
        ]
        
        # Global operation keywords
        global_keywords = {
            "summary": ["summary", "summarize", "summarization", "tl;dr"],
            "compare": ["compare", "comparison", "vs", "versus", "difference", "different"],
            "translate": ["translate", "translation", "convert", "rephrase"],
            "rewrite": ["rewrite", "simplify", "paraphrase", "easier"],
            "overview": ["overview", "big picture", "high level", "general"],
            "bullet": ["bullet", "bullets", "points", "list"]
        }
        
        # Check out-of-context first
        if any(kw in query_lower for kw in out_of_context_keywords):
            return {
                "scope": QueryScope.OUT_OF_CONTEXT,
                "operation": None,
                "reason": "Detected casual/greeting query",
                "confidence": 0.8,
                "is_global": False,
                "is_local": False,
                "is_out_of_context": True,
            }
        
        # Check global operations
        for operation, keywords in global_keywords.items():
            if any(kw in query_lower for kw in keywords):
                logger.info(f"🔍 Fallback: Detected GLOBAL operation: {operation}")
                return {
                    "scope": QueryScope.GLOBAL,
                    "operation": operation,
                    "reason": f"Detected {operation} operation keyword",
                    "confidence": 0.75,
                    "is_global": True,
                    "is_local": False,
                    "is_out_of_context": False,
                }
        
        # Default to local
        logger.info("🔍 Fallback: Defaulting to LOCAL scope")
        return {
            "scope": QueryScope.LOCAL,
            "operation": None,
            "reason": "No global operation detected, treating as local query",
            "confidence": 0.7,
            "is_global": False,
            "is_local": True,
            "is_out_of_context": False,
        }
