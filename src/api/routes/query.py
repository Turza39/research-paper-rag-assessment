"""
API routes for the research paper RAG system.
Enhanced with context awareness, metadata tracking, and improved query handling.
"""
from fastapi import APIRouter, HTTPException, Depends
from src.models.api import QueryRequest, QueryResponse, ErrorResponse
from src.models.history import ResearchQueryHistory
from src.services.rag_pipeline import RAGPipeline
from src.services.mongodb_service import get_mongodb
from typing import Annotated, Optional
from time import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()


# Extend QueryRequest to include research_id and research_name
class ExtendedQueryRequest(QueryRequest):
    research_id: Optional[str] = None
    research_name: Optional[str] = None


async def get_rag_pipeline():
    try:
        pipeline = RAGPipeline()
        yield pipeline
    finally:
        pass


@router.post("/query", 
             response_model=QueryResponse,
             responses={
                 400: {"model": ErrorResponse},
                 500: {"model": ErrorResponse}
             })
async def query_papers(
    query_request: ExtendedQueryRequest,
    pipeline: Annotated[RAGPipeline, Depends(get_rag_pipeline)],
    mongodb = Depends(get_mongodb)
):
    """
    Process a query against research papers.
    Features:
    - Context-aware query classification
    - Hallucination prevention
    - Section-specific retrieval
    - Low-confidence handling with clarification prompts
    - Comprehensive metadata tracking for analytics
    """
    try:
        logger.info(f"📥 Received query: {query_request.model_dump()}")
        
        # Process query through enhanced RAG pipeline
        response = await pipeline.query(
            query_text=query_request.question,
            paper_filter=query_request.expected_papers
        )

        logger.info(f"✅ Query processed successfully")
        logger.debug(f"Response metadata - Context: {response.context_level}, Query Type: {response.query_type}")

        # ✅ Store comprehensive analytics metadata
        try:
            # Store in general query history (for analytics)
            analytics_entry = {
                "question": query_request.question,
                "answer": response.answer,
                "response_time_ms": response.response_time_ms,
                "papers_referenced": response.sources_used,
                "citations_count": len(response.citations),
                # Enhanced metadata
                "context_score": response.context_score,
                "context_level": response.context_level,
                "query_type": response.query_type,
                "detected_section": response.detected_section,
                "is_out_of_context": response.is_out_of_context,
                "clarification_needed": response.clarification_needed,
                "confidence": response.confidence,
                "retrieval_count": response.retrieval_count,
            }
            
            await mongodb.store_general_chat_entry(
                question=query_request.question,
                answer=response.answer,
                response_time=response.response_time_ms / 1000.0 if response.response_time_ms else 0.0,
                papers_referenced=response.sources_used,
                metadata=analytics_entry  # Store all metadata
            )
            logger.info("✅ Stored in general query history with metadata")
        except Exception as e:
            logger.warning(f"⚠️ Failed to store general query: {str(e)}")

        # ✅ Store research-specific chat history if research_id provided
        if hasattr(query_request, 'research_id') and query_request.research_id:
            try:
                await mongodb.store_research_chat_entry(
                    research_id=query_request.research_id,
                    research_name=getattr(query_request, 'research_name', 'Untitled Research'),
                    question=query_request.question,
                    answer=response.answer,
                    papers_referenced=response.sources_used,
                    citations=[c.model_dump() for c in response.citations],
                    sources_used=response.sources_used,
                    response_time=response.response_time_ms / 1000.0 if response.response_time_ms else 0.0,
                    response_time_ms=response.response_time_ms,
                    confidence=response.confidence,
                    query_type=query_request.type.value,
                    difficulty=query_request.difficulty.value,
                    success=True,
                    context_score=response.context_score,
                    context_level=response.context_level,
                    detected_section=response.detected_section,
                    is_out_of_context=response.is_out_of_context,
                    clarification_needed=response.clarification_needed,
                    retrieval_count=response.retrieval_count
                )
                logger.info(f"✅ Stored in research chat history for {query_request.research_id}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to store research chat: {str(e)}")

        return response

    except Exception as e:
        logger.error(f"❌ Query failed: {str(e)}", exc_info=True)
        
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )