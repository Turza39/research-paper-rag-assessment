"""
Query history and analytics endpoints.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime, timedelta
from src.models.history import QueryHistory, PopularTopic
from src.services.mongodb_service import MongoDBService

router = APIRouter()

async def get_mongodb():
    service = MongoDBService()
    try:
        await service.initialize()
        yield service
    finally:
        pass

@router.get("/queries/history", response_model=List[QueryHistory])
async def get_query_history(
    mongodb: MongoDBService = Depends(get_mongodb),
    limit: int = 50
):
    """Get recent query history."""
    try:
        history = await mongodb.get_query_history(limit=limit)

        # Convert ObjectId to string
        for query in history:
            if "_id" in query:
                query["_id"] = str(query["_id"])

        return [QueryHistory(**query) for query in history]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/popular", response_model=List[PopularTopic])
async def get_popular_topics(
    mongodb: MongoDBService = Depends(get_mongodb),
    days: int = 30,
    limit: int = 10
):
    """Get most queried topics with analytics."""
    try:
        topics = await mongodb.get_popular_topics(days=days, limit=limit)
        return [PopularTopic(**topic) for topic in topics]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))