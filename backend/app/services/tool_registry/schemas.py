"""
schemas.py

Pydantic models for tool registry.
"""

from typing import List, Optional
from pydantic import BaseModel


class ToolInfo(BaseModel):
    name: str
    description: str
    category: str = ""
    keywords: List[str] = []
    tool_class: str = ""
    examples: List[str] = []


class ToolSearchResult(BaseModel):
    name: str
    description: str
    semantic_anchor: str = ""
    intent_type: str = ""
    tool_family: str = ""
    category: str = ""
    keywords: List[str] = []
    score: float = 0.0
    vector_score: float = 0.0
    keyword_score: float = 0.0
    fuzzy_score: float = 0.0
    negative_penalty: float = 1.0


class ToolSearchResponse(BaseModel):
    tools: List[ToolSearchResult]
    total: int
    query: str
