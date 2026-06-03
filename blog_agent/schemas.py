"""
blog_agent/schemas.py — Pydantic models and LangGraph State for the Blog Writer Agent.
"""
from __future__ import annotations

import operator
from typing import Annotated, List, Literal, Optional, TypedDict

from pydantic import BaseModel, Field


class Task(BaseModel):
    """A single section/task within the blog plan."""

    id: int
    title: str
    goal: str = Field(..., description="One sentence describing what the reader should understand.")
    bullets: List[str] = Field(..., min_length=3, max_length=6)
    target_words: int = Field(..., description="Target word count (120–550).")
    tags: List[str] = Field(default_factory=list)
    requires_research: bool = False
    requires_citations: bool = False
    requires_code: bool = False


class Plan(BaseModel):
    """Structured blog plan produced by the Orchestrator agent."""

    blog_title: str
    audience: str
    tone: str
    blog_kind: Literal[
        "explainer", "tutorial", "news_roundup", "comparison", "system_design"
    ] = "explainer"
    constraints: List[str] = Field(default_factory=list)
    tasks: List[Task]


class EvidenceItem(BaseModel):
    """A single piece of web evidence returned by Tavily research."""

    title: str
    url: str
    published_at: Optional[str] = None  # ISO "YYYY-MM-DD" preferred
    snippet: Optional[str] = None
    source: Optional[str] = None


class RouterDecision(BaseModel):
    """Structured output of the Router agent."""

    needs_research: bool
    mode: Literal["closed_book", "hybrid", "open_book"]
    reason: str
    queries: List[str] = Field(default_factory=list)
    max_results_per_query: int = Field(5)


class EvidencePack(BaseModel):
    """Structured output from the research synthesizer."""

    evidence: List[EvidenceItem] = Field(default_factory=list)


class ImageSpec(BaseModel):
    """Specification for a single AI-generated image."""

    placeholder: str = Field(..., description='e.g. [[IMAGE_1]]')
    filename: str = Field(..., description="Filename under images/, e.g. qkv_flow.png")
    alt: str
    caption: str
    prompt: str = Field(..., description="Prompt sent to the image model.")
    size: Literal["1024x1024", "1024x1536", "1536x1024"] = "1024x1024"
    quality: Literal["low", "medium", "high"] = "medium"


class GlobalImagePlan(BaseModel):
    """Output of the Image Planner — markdown with placeholders + image specs."""

    md_with_placeholders: str
    images: List[ImageSpec] = Field(default_factory=list)


class State(TypedDict):
    """Shared LangGraph state passed between every node in the pipeline."""

    topic: str

    # routing / research
    mode: str
    needs_research: bool
    queries: List[str]
    evidence: List[EvidenceItem]
    plan: Optional[Plan]

    # recency
    as_of: str
    recency_days: int

    # workers — annotated so parallel sections accumulate via operator.add
    sections: Annotated[List[tuple[int, str]], operator.add]

    # reducer / image
    merged_md: str
    md_with_placeholders: str
    image_specs: List[dict]

    final: str
