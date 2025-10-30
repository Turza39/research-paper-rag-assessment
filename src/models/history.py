"""
Models for paper management and query history.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class PaperStats(BaseModel):
    total_queries: int = 0
    avg_relevance_score: float = 0.0
    total_citations: int = 0
    last_queried: Optional[datetime] = None

class QueryHistory(BaseModel):
    id: str = Field(..., description="Unique query ID")
    question: str
    papers_referenced: List[str]
    response_time: float  # in seconds
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_rating: Optional[int] = Field(None, ge=1, le=5)
    query_type: str
    difficulty: str
    success: bool = True
    error_message: Optional[str] = None

class PopularTopic(BaseModel):
    topic: str
    query_count: int
    avg_response_time: float
    success_rate: float
    last_queried: datetime