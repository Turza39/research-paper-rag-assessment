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
    Process a query against research papers and log it to MongoDB.
    """
    from time import time
    from src.services.mongodb_service import get_mongodb
    
    mongodb = await get_mongodb()
    
    start_time = time()
    try:
        # Process query through RAG pipeline
        response = await pipeline.query(
            query_text=query_request.question,
            paper_filter=query_request.expected_papers
        )
        response_time = time() - start_time

        # Store query history in MongoDB
        await mongodb.store_query({
            "question": query_request.question,
            "papers_referenced": [c.metadata.get("file_name", "unknown") for c in getattr(response, "citations", [])],
            "response_time": response_time,
            "query_type": "rag",
            "difficulty": "medium",
            "success": True
        })

        return response

    except Exception as e:
        response_time = time() - start_time
        # Log failed query
        await mongodb.store_query({
            "question": query_request.question,
            "papers_referenced": [],
            "response_time": response_time,
            "query_type": "rag",
            "difficulty": "medium",
            "success": False,
            "error_message": str(e)
        })
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )

