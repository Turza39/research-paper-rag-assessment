"""
Data models for paper storage and retrieval.
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field

class Section(BaseModel):
    """Paper section with content and metadata."""
    title: str
    content: str
    page_start: int
    page_end: int
    vector_ids: List[str] = Field(default_factory=list)

class Citation(BaseModel):
    """Citation information for query responses."""
    paper_title: str
    section: str
    page: int
    relevance_score: float

class Chunk(BaseModel):
    """Text chunk with metadata."""
    text: str
    metadata: Dict[str, Any]
    vector_id: Optional[str] = None

class QueryResponse(BaseModel):
    """Response format for RAG queries."""
    answer: str
    citations: List[Citation]
    sources_used: List[str]
    confidence: float

class Paper(BaseModel):
    """Main paper model with metadata and sections."""
    title: str
    authors: List[str]
    year: Optional[int]
    abstract: str
    sections: Dict[str, Section]
    file_path: str
    page_count: int
    processed_date: datetime = Field(default_factory=datetime.utcnow)
    vector_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
