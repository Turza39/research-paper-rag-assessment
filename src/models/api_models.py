"""
API request and response models.
"""
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class QueryType(str, Enum):
    SINGLE_PAPER = "single-paper"
    MULTI_PAPER = "multi-paper"
    CROSS_DOMAIN = "cross-domain"

class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class QueryRequest(BaseModel):
    id: int
    question: str
    expected_papers: List[str]
    difficulty: DifficultyLevel
    type: QueryType

class Citation(BaseModel):
    paper_title: str
    section: str
    page: int
    relevance_score: float = Field(..., ge=0.0, le=1.0)

class QueryResponse(BaseModel):
    answer: str
    citations: List[Citation]
    sources_used: List[str]
    confidence: float = Field(..., ge=0.0, le=1.0)