"""
Data models for the application.
"""
from pydantic import BaseModel
from typing import Optional, List

class Paper(BaseModel):
    """Model for a research paper."""
    title: str
    authors: List[str]
    year: Optional[int]
    abstract: str
    full_text: str
    sections: dict  # Map of section names to content
    page_count: int