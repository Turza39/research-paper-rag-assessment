"""
Data models for research topics and management.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ResearchTopic(BaseModel):
    """Research topic model for database storage."""
    id: Optional[str] = Field(default=None, alias="_id")
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    papers: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = Field(default=None)  # For future user tracking
    tags: List[str] = Field(default_factory=list)
    is_archived: bool = Field(default=False)

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class ResearchTopicCreate(BaseModel):
    """Schema for creating a new research topic."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    papers: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class ResearchTopicUpdate(BaseModel):
    """Schema for updating a research topic."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    papers: Optional[List[str]] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)
    is_archived: Optional[bool] = Field(default=None)


class ResearchTopicResponse(BaseModel):
    """Response model for research topic (for API responses)."""
    id: str = Field(alias="_id")
    name: str
    description: Optional[str]
    papers: List[str]
    created_at: datetime
    updated_at: datetime
    tags: List[str]
    is_archived: bool

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={datetime: lambda v: v.isoformat()}
    )
