"""
Data models for research-specific chat history.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ResearchCitation(BaseModel):
    """Citation information from research queries."""
    paper_title: str
    section: str
    page: int
    relevance_score: float = Field(..., ge=0.0, le=1.0)


class ResearchChatEntry(BaseModel):
    """Research-specific chat history entry (for storage)."""
    id: Optional[str] = Field(default=None, alias="_id")
    research_id: str
    research_name: str
    question: str
    answer: str
    papers_referenced: List[str]
    citations: List[ResearchCitation] = []
    sources_used: List[str] = []
    response_time: float
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    query_type: str = "single-paper"
    difficulty: str = "medium"
    success: bool = True
    error_message: Optional[str] = None
    user_rating: Optional[int] = Field(default=None, ge=1, le=5)
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class ResearchChatResponse(BaseModel):
    """Response model for research chat entry (for API responses)."""
    id: str = Field(alias="_id")
    research_id: str
    research_name: str
    question: str
    answer: str
    papers_referenced: List[str]
    citations: List[ResearchCitation]
    response_time: float
    confidence: float
    timestamp: str
    user_rating: Optional[int] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class ResearchChatStats(BaseModel):
    """Statistics for research topic chat history."""
    research_id: str
    research_name: str
    total_queries: int
    successful_queries: int
    failed_queries: int
    success_rate: float
    avg_response_time: float
    avg_confidence: float
    total_papers_referenced: int
    unique_papers: List[str]
    last_query_time: Optional[datetime] = None
    most_referenced_papers: List[Dict[str, Any]]


class DeleteResearchChatRequest(BaseModel):
    """Request to delete research chat history."""
    confirm: bool = False


class DeleteResearchChatResponse(BaseModel):
    """Response after deleting research chat history."""
    deleted_count: int
    research_id: str
    research_name: str
    message: str