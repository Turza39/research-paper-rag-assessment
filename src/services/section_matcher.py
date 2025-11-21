"""
Service for matching and extracting sections from research papers.
Handles context-specific retrieval based on detected sections.
"""
from typing import List, Dict, Optional, Tuple
import logging
from src.services.vector_store import VectorStore

logger = logging.getLogger(__name__)


class SectionMatcher:
    """Match and extract specific sections from papers."""

    SECTION_KEYWORDS = {
        "abstract": ["abstract", "summary", "overview"],
        "introduction": ["introduction", "intro", "background", "related work", "motivation"],
        "methodology": ["methodology", "method", "approach", "framework", "architecture", "system", "design"],
        "results": ["results", "result", "findings", "experiments", "experimental", "evaluation", "performance"],
        "conclusion": ["conclusion", "conclusions", "final", "summary"],
        "discussion": ["discussion", "analysis", "implications", "impact"],
        "future_work": ["future work", "future research", "future directions", "limitations", "open problems"],
        "references": ["references", "citations", "bibliography"],
    }

    def __init__(self):
        """Initialize section matcher."""
        self.vector_store = VectorStore()

    async def retrieve_section(
        self,
        query: str,
        section_name: str,
        paper_filter: Optional[List[str]] = None,
        limit: int = 5
    ) -> List[Dict]:
        """
        Retrieve specific section chunks from papers.
        
        Args:
            query: User query
            section_name: Detected section (e.g., "methodology", "results")
            paper_filter: List of paper names to search
            limit: Max results to return
        
        Returns:
            List of relevant chunks from the specified section
        """
        # Add section-specific context to query
        section_query = f"{query} {section_name}"
        
        # Get embeddings for the enhanced query
        from src.services.embedding_service import EmbeddingService
        embedding_service = EmbeddingService()
        query_vector = embedding_service.get_embedding(section_query)
        
        # Search with enhanced context
        results = self.vector_store.search_similar(
            query_vector=query_vector,
            paper_filter=paper_filter,
            limit=limit * 2  # Get more to filter
        )
        
        # Filter results by section relevance
        section_results = self._filter_by_section(results, section_name)
        
        return section_results[:limit]

    def _filter_by_section(self, results: List[Dict], target_section: str) -> List[Dict]:
        """
        Filter and boost results by section relevance.
        
        Strategy:
        1. Exact section matches get highest priority
        2. Related section matches get medium priority  
        3. Keyword matches in text get low priority
        4. Sort by boosted score
        """
        section_keywords = self.SECTION_KEYWORDS.get(target_section.lower(), [])
        target_lower = target_section.lower()
        
        # Define section aliases (what sections can match what queries)
        section_aliases = {
            "abstract": ["abstract", "summary", "overview"],
            "introduction": ["introduction", "intro", "related work", "background"],
            "methodology": ["methodology", "method", "approach", "framework", "design", "system"],
            "results": ["results", "findings", "experiments", "evaluation", "performance"],
            "conclusion": ["conclusion", "conclusions", "summary"],
            "discussion": ["discussion", "analysis"],
            "future_work": ["future work", "limitations"],
            "references": ["references", "citations"],
        }
        
        matched_aliases = section_aliases.get(target_lower, [])
        
        filtered = []
        for result in results:
            metadata = result.get("metadata", {})
            detected_section = metadata.get("section", "").lower()
            text = result.get("text", "").lower()
            
            # Calculate score boost
            score_boost = 0.0
            
            # HIGHEST: Exact section match
            if detected_section == target_lower:
                score_boost = 0.25
                logger.info(f"✅ Exact match: {detected_section} for target {target_section}")
            
            # HIGH: Alias match
            elif detected_section in matched_aliases or any(alias in detected_section for alias in matched_aliases):
                score_boost = 0.15
                logger.debug(f"🔄 Alias match: {detected_section} for target {target_section}")
            
            # MEDIUM: Keywords in text
            else:
                keyword_count = sum(1 for kw in section_keywords if kw in text)
                if keyword_count > 0:
                    score_boost = min(0.15, keyword_count * 0.03)
                    logger.debug(f"🔑 Keyword match ({keyword_count} keywords found): {detected_section}")
            
            # Apply score boost
            original_score = result.get("score", 0.0)
            result["score"] = min(1.0, original_score + score_boost)
            result["section_boost"] = score_boost
            filtered.append(result)
        
        # Sort by boosted score (descending)
        filtered.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        
        # Log filtering results
        logger.info(f"🎯 Section filtering: {len(results)} results → {len(filtered)} after filtering for '{target_section}'")
        
        return filtered

    def detect_section_from_chunks(self, chunks: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Organize chunks by detected section.
        
        Returns:
            Dict mapping section names to lists of chunks
        """
        sections = {section: [] for section in self.SECTION_KEYWORDS.keys()}
        
        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            detected_section = metadata.get("section", "").lower()
            text = chunk.get("text", "").lower()
            
            # Try to match detected section
            best_match = None
            for section_name, keywords in self.SECTION_KEYWORDS.items():
                if detected_section == section_name:
                    best_match = section_name
                    break
                # Check for keywords in text as fallback
                if any(kw in text for kw in keywords):
                    best_match = section_name
                    break
            
            if best_match:
                sections[best_match].append(chunk)
            else:
                sections.setdefault("other", []).append(chunk)
        
        # Remove empty sections
        return {k: v for k, v in sections.items() if v}

    @staticmethod
    def get_section_description(section_name: str) -> str:
        """Get description of what a section typically contains."""
        descriptions = {
            "abstract": "Brief overview of the paper's purpose, methods, and findings",
            "introduction": "Background, motivation, and related work leading to the research",
            "methodology": "Research methods, frameworks, and technical approach used",
            "results": "Experimental findings, data, and quantitative results",
            "conclusion": "Summary of findings, implications, and future directions",
            "discussion": "In-depth analysis and interpretation of results",
            "future_work": "Suggested areas for future research and current limitations",
            "references": "Cited sources and bibliography",
        }
        return descriptions.get(section_name.lower(), "Paper section content")
