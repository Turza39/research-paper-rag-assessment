"""
Service for handling sequential summarization to prevent token limit overflow.
Handles large global queries like summarization across multiple papers.
"""
from typing import List, Dict, Optional, Tuple
import logging
from src.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class SequentialSummarizer:
    """Handle sequential summarization for large queries across multiple papers."""

    MAX_TOKENS_PER_SUMMARY = 1500  # Conservative limit
    SUMMARY_CHUNK_SIZE = 5  # Summarize in chunks to manage token flow

    def __init__(self):
        """Initialize summarizer."""
        self.embedding_service = EmbeddingService()

    async def generate_sequential_summary(
        self,
        papers: List[str],
        query: str,
        summary_type: str = "general"
    ) -> Dict:
        """
        Generate summary across multiple papers sequentially to manage tokens.
        
        Args:
            papers: List of paper names/IDs
            query: User query (e.g., "summarize", "overview")
            summary_type: Type of summary ("general", "abstract", "results", etc.)
        
        Returns:
            Dict with sequential summaries and metadata
        """
        summaries = {}
        combined_context = ""
        tokens_used = 0

        for paper in papers:
            try:
                # Generate summary for individual paper
                paper_summary = await self._summarize_paper(
                    paper,
                    summary_type,
                    MAX_TOKENS=self.MAX_TOKENS_PER_SUMMARY
                )
                
                summaries[paper] = paper_summary
                
                # Track tokens
                estimated_tokens = self._estimate_tokens(paper_summary)
                tokens_used += estimated_tokens
                
                # Build combined context if not exceeding limits
                if tokens_used < 6000:  # Leave room for response
                    combined_context += f"\n\n📄 {paper}:\n{paper_summary['summary']}"
                
            except Exception as e:
                logger.warning(f"Failed to summarize paper {paper}: {e}")
                summaries[paper] = {"summary": f"Error summarizing {paper}", "error": str(e)}

        return {
            "individual_summaries": summaries,
            "combined_context": combined_context,
            "total_papers_summarized": len([s for s in summaries.values() if "error" not in s]),
            "tokens_estimated": tokens_used,
            "can_combine": tokens_used < 6000
        }

    async def _summarize_paper(
        self,
        paper_id: str,
        summary_type: str,
        MAX_TOKENS: int = 1500
    ) -> Dict:
        """
        Generate focused summary for a single paper.
        
        Args:
            paper_id: Paper identifier
            summary_type: Type of summary to generate
            MAX_TOKENS: Maximum tokens for summary
        
        Returns:
            Dict with summary and metadata
        """
        from src.services.mongodb_service import MongoDBService
        from src.services.vector_store import VectorStore

        try:
            mongodb = MongoDBService()
            vector_store = VectorStore()

            # Get paper chunks from MongoDB
            chunks = await mongodb.get_paper_chunks(paper_id)
            
            if not chunks:
                return {"summary": f"No content found for {paper_id}", "paper_id": paper_id}

            # Filter chunks based on summary type
            relevant_chunks = self._filter_chunks_for_summary(chunks, summary_type)
            
            # Prepare context with token limit awareness
            context = self._prepare_token_limited_context(relevant_chunks, MAX_TOKENS)

            # Generate summary using Gemini
            prompt = self._build_summary_prompt(
                paper_id,
                summary_type,
                context,
                MAX_TOKENS
            )

            response = self.embedding_service.gemini.generate_content(prompt)
            
            return {
                "paper_id": paper_id,
                "summary_type": summary_type,
                "summary": response.text,
                "chunks_used": len(relevant_chunks),
            }

        except Exception as e:
            logger.error(f"Error in _summarize_paper for {paper_id}: {e}")
            return {"summary": f"Error generating summary: {str(e)}", "error": str(e)}

    def _filter_chunks_for_summary(self, chunks: List[Dict], summary_type: str) -> List[Dict]:
        """Filter chunks relevant to summary type."""
        if summary_type == "abstract":
            # Prioritize abstract sections
            return [
                c for c in chunks 
                if c.get("section", "").lower() in ["abstract", "summary"]
            ] or chunks[:5]
        
        elif summary_type == "results":
            # Prioritize results sections
            return [
                c for c in chunks 
                if c.get("section", "").lower() in ["results", "findings", "evaluation"]
            ] or chunks[:10]
        
        elif summary_type == "methodology":
            # Prioritize methodology sections
            return [
                c for c in chunks 
                if c.get("section", "").lower() in ["methodology", "method", "approach"]
            ] or chunks[:10]
        
        else:  # general summary
            # Take diverse chunks from throughout paper
            total = len(chunks)
            indices = [
                0,  # First chunk (usually title/intro)
                total // 4,
                total // 2,
                3 * total // 4,
                total - 1  # Last chunk (usually conclusion)
            ]
            return [chunks[i] for i in indices if 0 <= i < total]

    def _prepare_token_limited_context(self, chunks: List[Dict], max_tokens: int) -> str:
        """Prepare context while respecting token limits."""
        context = ""
        token_count = 0

        for chunk in chunks:
            chunk_text = chunk.get("text", "")
            chunk_tokens = self._estimate_tokens(chunk_text)
            
            if token_count + chunk_tokens <= max_tokens * 0.7:  # Use 70% for content
                context += f"\n{chunk_text}"
                token_count += chunk_tokens
            else:
                break

        return context

    def _build_summary_prompt(
        self,
        paper_id: str,
        summary_type: str,
        context: str,
        max_tokens: int
    ) -> str:
        """Build summary generation prompt."""
        prompts = {
            "abstract": f"Summarize the main purpose, methodology, and findings of this paper in 2-3 sentences:\n\n{context}",
            "results": f"Summarize the key results and findings from this paper:\n\n{context}",
            "methodology": f"Summarize the research methodology and approach used in this paper:\n\n{context}",
            "general": f"Provide a concise overview of this paper including its purpose, methods, and conclusions:\n\n{context}",
        }

        base_prompt = prompts.get(summary_type, prompts["general"])
        
        return f"""{base_prompt}

Keep the summary concise (under {max_tokens} tokens) and focus on key points only.
Do not add information not present in the provided text."""

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """
        Rough estimate of tokens (1 token ≈ 4 characters).
        More accurate: use tiktoken if available.
        """
        return len(text) // 4

    async def merge_summaries(
        self,
        individual_summaries: Dict[str, Dict],
        query: str
    ) -> str:
        """
        Merge individual paper summaries into cohesive response.
        Uses minimal tokens for merging.
        """
        summaries_text = "\n\n".join([
            f"📄 {paper}: {data.get('summary', '')}"
            for paper, data in individual_summaries.items()
            if "error" not in data
        ])

        prompt = f"""Based on these individual paper summaries, provide a unified overview:

{summaries_text}

Original query: {query}

Provide a cohesive synthesis of the papers in 2-3 sentences, highlighting key commonalities or differences."""

        response = self.embedding_service.gemini.generate_content(prompt)
        return response.text
