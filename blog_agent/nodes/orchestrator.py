"""
blog_agent/nodes/orchestrator.py — Orchestrator agent.

Produces a fully structured Plan (5–9 tasks) from the topic and evidence.
"""
from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from blog_agent.config import MAX_EVIDENCE_FOR_PLAN, llm
from blog_agent.schemas import Plan, State

ORCH_SYSTEM = """You are a senior technical writer and developer advocate.
Produce a highly actionable outline for a technical blog post.

Requirements:
- 5–9 tasks, each with goal + 3–6 bullets + target_words.
- Tags are flexible; do not force a fixed taxonomy.

Grounding:
- closed_book: evergreen, no evidence dependence.
- hybrid: use evidence for up-to-date examples; mark those tasks requires_research=True and requires_citations=True.
- open_book: weekly/news roundup:
  - Set blog_kind="news_roundup"
  - No tutorial content unless requested
  - If evidence is weak, reflect that — don't invent events.

Output must match Plan schema.
"""


def orchestrator_node(state: State) -> dict:
    """Generates a structured blog Plan from topic, mode, and available evidence."""
    planner = llm.with_structured_output(Plan)
    mode = state.get("mode", "closed_book")
    evidence = state.get("evidence", [])
    forced_kind = "news_roundup" if mode == "open_book" else None

    plan = planner.invoke([
        SystemMessage(content=ORCH_SYSTEM),
        HumanMessage(content=(
            f"Topic: {state['topic']}\n"
            f"Mode: {mode}\n"
            f"As-of: {state['as_of']} (recency_days={state['recency_days']})\n"
            f"{'Force blog_kind=news_roundup' if forced_kind else ''}\n\n"
            f"Evidence:\n{[e.model_dump() for e in evidence][:MAX_EVIDENCE_FOR_PLAN]}"
        )),
    ])

    if forced_kind:
        plan.blog_kind = "news_roundup"

    return {"plan": plan}
