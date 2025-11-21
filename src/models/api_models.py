"""
API request and response models.
"""
from enum import Enum
from typing import List, Optional, Dict, Any
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
    # New fields for enhanced context awareness
    context_score: float = Field(default=0.7, ge=0.0, le=1.0)  # Overall relevance score
    context_level: str = Field(default="medium", description="high|medium|low|very_low")
    query_type: str = Field(default="context_specific", description="Type of query detected")
    detected_section: Optional[str] = Field(default=None, description="Paper section detected in query")
    is_out_of_context: bool = Field(default=False, description="Whether query is out of research context")
    clarification_needed: bool = Field(default=False, description="Whether clarification is needed")
    clarification_prompt: Optional[str] = Field(default=None, description="Prompt for user clarification if needed")
    warning_message: Optional[str] = Field(default=None, description="Warning about low confidence or hallucination risk")
    retrieval_count: int = Field(default=0, description="Number of chunks retrieved")
    response_time_ms: Optional[float] = Field(default=None, description="Response generation time in milliseconds")