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

@router.get("/analytics/popular")
async def get_popular_topics(
    mongodb: MongoDBService = Depends(get_mongodb),
    days: int = 30,
    limit: int = 10
):
    """Get most queried topics with a Gemini-generated summary."""
    try:
        topics = await mongodb.get_popular_topics(days=days, limit=limit)
        topic_models = [PopularTopic(**topic) for topic in topics]

        # ---- Gemini Summarization ----
        import os, google.generativeai as genai
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

        topics_text = "\n".join([
            f"Question: '{t.topic}' - {t.query_count} queries, "
            f"{t.success_rate*100:.1f}% success rate, "
            f"avg response time: {t.avg_response_time:.2f}s"
            for t in topic_models
        ])
        
        prompt = (
            "Summarize the following query analytics in 2-3 sentences, "
            "highlighting the most popular questions and key trends:\n\n" + topics_text
        )

        model = genai.GenerativeModel("gemini-2.5-flash")
        gemini_response = model.generate_content(prompt)
        summary = gemini_response.text.strip() if hasattr(gemini_response, "text") else "No summary available."

        return {
            "topics": [t.dict() for t in topic_models],
            "summary": summary
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))