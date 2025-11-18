# src/models/history.py - COMPLETE VERSION

"""
Models for paper management and query history.
Consolidates analytics (QueryHistory) with chat display (ResearchQueryHistory).
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Citation(BaseModel):
    """Citation information."""
    paper_title: str
    section: str
    page: int
    relevance_score: float


class PaperStats(BaseModel):
    """Paper statistics."""
    total_queries: int = 0
    avg_relevance_score: float = 0.0
    total_citations: int = 0
    last_queried: Optional[datetime] = None


class QueryHistory(BaseModel):
    """
    General query history - for analytics, trending, and tracking.
    Stored in 'query_history' collection.
    """
    id: str = Field(..., alias="_id")
    question: str
    papers_referenced: List[str]
    response_time: float
    timestamp: datetime
    user_rating: Optional[int] = None
    query_type: str
    difficulty: str
    success: bool = True
    error_message: Optional[str] = None

    model_config = {"populate_by_name": True}


class ResearchQueryHistory(BaseModel):
    """
    Research-specific query history - for chat display and tracking.
    Stored in 'research_chat_history' collection.
    Includes citations for reference display.
    """
    id: str = Field(..., alias="_id")
    research_id: str
    research_name: str
    question: str
    answer: str
    papers_referenced: List[str]
    citations: List[Citation] = []
    sources_used: List[str] = []
    response_time: float
    confidence: float = 0.0
    timestamp: datetime
    query_type: str = "single-paper"
    difficulty: str = "medium"
    success: bool = True
    error_message: Optional[str] = None
    user_rating: Optional[int] = None

    model_config = {"populate_by_name": True}


class PopularTopic(BaseModel):
    """Popular/trending topics from analytics."""
    topic: str
    query_count: int
    avg_response_time: float
    success_rate: float
    last_queried: datetime