"""
API routes for research-specific chat history.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional
from src.models.history import ResearchQueryHistory
from src.services.mongodb_service import get_mongodb
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class ResearchChatResponse(Dict[str, Any]):
    """Response model for research chat entry."""
    pass


@router.get("/research/{research_id}/chat-history")
async def get_research_chat_history(
    research_id: str,
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    mongodb = Depends(get_mongodb)
):
    """Get chat history for a specific research topic."""
    try:
        logger.info(f"📥 Fetching chat history for research: {research_id}")
        
        history = await mongodb.get_research_chat_history(
            research_id=research_id,
            limit=limit,
            skip=skip
        )
        
        if not history:
            logger.info(f"ℹ️ No chat history found for research: {research_id}")
            return []
        
        logger.info(f"✅ Retrieved {len(history)} chat entries for {research_id}")
        return history
    except Exception as e:
        logger.error(f"❌ Error retrieving research chat history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/research/{research_id}/chat-stats")
async def get_research_chat_stats(
    research_id: str,
    mongodb = Depends(get_mongodb)
):
    """Get statistics for research topic chat history."""
    try:
        logger.info(f"📊 Fetching chat stats for research: {research_id}")
        
        stats = await mongodb.get_research_chat_stats(research_id)
        
        if not stats:
            raise HTTPException(
                status_code=404,
                detail=f"No chat history found for research topic: {research_id}"
            )
        
        logger.info(f"✅ Retrieved stats for {research_id}")
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error retrieving research chat stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/research/{research_id}/chat-history")
async def delete_research_chat_history(
    research_id: str,
    mongodb = Depends(get_mongodb)
):
    """Delete all chat history for a specific research topic."""
    try:
        logger.warning(f"🗑️ Deleting chat history for research: {research_id}")
        
        deleted_count = await mongodb.delete_research_chat_history(research_id)
        
        logger.info(f"✅ Deleted {deleted_count} research chat entries for {research_id}")
        
        return {
            "deleted_count": deleted_count,
            "research_id": research_id,
            "message": f"Successfully deleted {deleted_count} chat entries for this research topic"
        }
    except Exception as e:
        logger.error(f"❌ Error deleting research chat history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/general/history")
async def get_general_chat_history(
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    mongodb = Depends(get_mongodb)
):
    """Get general chat history."""
    try:
        logger.info(f"📥 Fetching general chat history (limit={limit}, skip={skip})")
        
        history = await mongodb.get_general_chat_history(limit=limit, skip=skip)
        
        if not history:
            logger.info("ℹ️ No general chat history found")
            return []
        
        logger.info(f"✅ Retrieved {len(history)} general chat entries")
        return history
    except Exception as e:
        logger.error(f"❌ Error retrieving general chat history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/chat/general/history")
async def delete_general_chat_history(
    mongodb = Depends(get_mongodb)
):
    """Delete all general chat history."""
    try:
        logger.warning("🗑️ Deleting all general chat history")
        
        deleted_count = await mongodb.delete_general_chat_history()
        
        logger.info(f"✅ Deleted {deleted_count} general chat entries")
        
        return {
            "deleted_count": deleted_count,
            "message": f"Successfully deleted {deleted_count} general chat entries"
        }
    except Exception as e:
        logger.error(f"❌ Error deleting general chat history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))