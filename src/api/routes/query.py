"""
API routes for the research paper RAG system.
"""
from fastapi import APIRouter, HTTPException, Depends
from src.models.api import QueryRequest, QueryResponse, ErrorResponse
from src.services.rag_pipeline import RAGPipeline
from typing import Annotated

router = APIRouter()

# Dependency to get RAG pipeline instance
async def get_rag_pipeline():
    try:
        pipeline = RAGPipeline()
        yield pipeline
    finally:
        # Clean up if needed
        pass

@router.post("/query", 
             response_model=QueryResponse,
             responses={
                 400: {"model": ErrorResponse},
                 500: {"model": ErrorResponse}
             })
async def query_papers(
    query_request: QueryRequest,
    pipeline: Annotated[RAGPipeline, Depends(get_rag_pipeline)]
):
    """
    Process a query against research papers.
    
    Parameters:
        query_request: QueryRequest model containing question and context
        pipeline: RAG pipeline instance (injected)
        
    Returns:
        QueryResponse with answer, citations, and confidence score
    """
    try:
        # Process query through RAG pipeline with paper filtering
        response = await pipeline.query(
            query_text=query_request.question,
            paper_filter=query_request.expected_papers
        )
        
        return response
        
    except Exception as e:
        # Log the error here
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )

