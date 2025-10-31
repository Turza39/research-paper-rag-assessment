"""
Models for paper management and query history.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from typing import List, Dict

class PaperStats(BaseModel):
    total_queries: int = 0
    avg_relevance_score: float = 0.0
    total_citations: int = 0
    last_queried: Optional[datetime] = None

class QueryHistory(BaseModel):
    id: str = Field(..., alias="_id")  # map MongoDB _id -> id
    question: str
    papers_referenced: List[str]
    response_time: float
    timestamp: datetime
    user_rating: Optional[int] = None
    query_type: str
    difficulty: str
    success: bool = True
    error_message: Optional[str] = None

    model_config = {
        "populate_by_name": True  # allows using 'id' in code but '_id' in data
    }
class PopularTopic(BaseModel):
    topic: str
    query_count: int
    avg_response_time: float
    success_rate: float
    last_queried: datetime