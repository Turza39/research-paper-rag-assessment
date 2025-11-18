"""
API routes for the research paper RAG system.
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
    Stores both general query history (for analytics) and research-specific chat history (for display).
    """
    start_time = time()
    
    try:
        logger.info(f"📥 Received query: {query_request.model_dump()}")
        
        # Process query through RAG pipeline
        response = await pipeline.query(
            query_text=query_request.question,
            paper_filter=query_request.expected_papers
        )
        response_time = time() - start_time

        logger.info(f"✅ Query successful in {response_time:.2f}s")

        # ✅ Store in general query history (for analytics)
        try:
            await mongodb.store_general_chat_entry(
                question=query_request.question,
                answer=response.answer,
                response_time=response_time,
                papers_referenced=response.sources_used
            )
            logger.info("✅ Stored in general query history")
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
                    response_time=response_time,
                    confidence=response.confidence,
                    query_type=query_request.type.value,
                    difficulty=query_request.difficulty.value,
                    success=True
                )
                logger.info(f"✅ Stored in research chat history for {query_request.research_id}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to store research chat: {str(e)}")

        return response

    except Exception as e:
        response_time = time() - start_time
        logger.error(f"❌ Query failed: {str(e)}")
        
        # Store failed query in general history
        try:
            await mongodb.store_query({
                "question": query_request.question,
                "papers_referenced": [],
                "response_time": response_time,
                "query_type": query_request.type.value,
                "difficulty": query_request.difficulty.value,
                "success": False,
                "error_message": str(e)
            })
        except:
            pass
        
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )