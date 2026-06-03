"""
blog_agent/nodes/worker.py — Worker agent.

Writes a single blog section. Multiple workers run in parallel
via LangGraph's Send() fan-out pattern.
"""
from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from blog_agent.config import MAX_EVIDENCE_FOR_WORKER, llm
from blog_agent.schemas import EvidenceItem, Plan, Task

WORKER_SYSTEM = """You are a senior technical writer and developer advocate.
Write ONE section of a technical blog post in Markdown.

Constraints:
- Cover ALL bullets in order.
- Target words ±15%.
- Output only section markdown starting with "## <Section Title>".

Scope guard:
- If blog_kind=="news_roundup", do NOT drift into tutorials. Focus on events + implications.

Grounding:
- If mode=="open_book": only introduce claims supported by provided Evidence URLs.
  Attach a Markdown link ([Source](URL)) for each supported claim.
  If unsupported, write "Not found in provided sources."
- If requires_citations==true (hybrid tasks): cite Evidence URLs for external claims.

Code:
- If requires_code==true, include at least one minimal, runnable snippet.
"""


def worker_node(payload: dict) -> dict:
    """Writes one blog section based on a Task spec. Called once per task in parallel."""
    task = Task(**payload["task"])
    plan = Plan(**payload["plan"])
    evidence = [EvidenceItem(**e) for e in payload.get("evidence", [])]

    bullets_text = "\n- " + "\n- ".join(task.bullets)
    evidence_text = "\n".join(
        f"- {e.title} | {e.url} | {e.published_at or 'date:unknown'}"
        for e in evidence[:MAX_EVIDENCE_FOR_WORKER]
    )

    section_md = llm.invoke([
        SystemMessage(content=WORKER_SYSTEM),
        HumanMessage(content=(
            f"Blog title: {plan.blog_title}\n"
            f"Audience: {plan.audience}\n"
            f"Tone: {plan.tone}\n"
            f"Blog kind: {plan.blog_kind}\n"
            f"Constraints: {plan.constraints}\n"
            f"Topic: {payload['topic']}\n"
            f"Mode: {payload.get('mode')}\n"
            f"As-of: {payload.get('as_of')} (recency_days={payload.get('recency_days')})\n\n"
            f"Section title: {task.title}\n"
            f"Goal: {task.goal}\n"
            f"Target words: {task.target_words}\n"
            f"Tags: {task.tags}\n"
            f"requires_research: {task.requires_research}\n"
            f"requires_citations: {task.requires_citations}\n"
            f"requires_code: {task.requires_code}\n"
            f"Bullets:{bullets_text}\n\n"
            f"Evidence (ONLY cite these URLs):\n{evidence_text}\n"
        )),
    ]).content.strip()

    return {"sections": [(task.id, section_md)]}
