"""
blog_agent/nodes/router.py — Router agent.

Classifies the topic (closed_book / hybrid / open_book) and decides
whether web research is needed before writing begins.
"""
from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from blog_agent.config import (
    CLOSED_BOOK_RECENCY_DAYS,
    HYBRID_RECENCY_DAYS,
    OPEN_BOOK_RECENCY_DAYS,
    llm,
)
from blog_agent.schemas import RouterDecision, State

ROUTER_SYSTEM = """You are a routing module for a technical blog planner.

Decide whether web research is needed BEFORE planning.

Modes:
- closed_book (needs_research=false): evergreen concepts.
- hybrid (needs_research=true): evergreen + needs up-to-date examples/tools/models.
- open_book (needs_research=true): volatile weekly/news/"latest"/pricing/policy.

If needs_research=true:
- Output 3–10 high-signal, scoped queries.
- For open_book weekly roundup, include queries reflecting last 7 days.
"""


def router_node(state: State) -> dict:
    """Classifies the topic and decides the research mode."""
    decider = llm.with_structured_output(RouterDecision)
    decision = decider.invoke([
        SystemMessage(content=ROUTER_SYSTEM),
        HumanMessage(content=f"Topic: {state['topic']}\nAs-of date: {state['as_of']}"),
    ])

    if decision.mode == "open_book":
        recency_days = OPEN_BOOK_RECENCY_DAYS
    elif decision.mode == "hybrid":
        recency_days = HYBRID_RECENCY_DAYS
    else:
        recency_days = CLOSED_BOOK_RECENCY_DAYS

    return {
        "needs_research": decision.needs_research,
        "mode": decision.mode,
        "queries": decision.queries,
        "recency_days": recency_days,
    }


def route_next(state: State) -> str:
    """Conditional edge: sends to 'research' or skips straight to 'orchestrator'."""
    return "research" if state["needs_research"] else "orchestrator"
