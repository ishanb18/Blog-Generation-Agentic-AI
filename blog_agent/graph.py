"""
blog_agent/graph.py — Builds and compiles the full LangGraph pipeline.

Graph topology:
    START → router → (research?) → orchestrator
                                        ↓ fanout (parallel)
                                    [worker × N]
                                        ↓ reduce
                                    reducer subgraph
                                        ↓
                                       END

The reducer is itself a subgraph:
    merge_content → decide_images → generate_and_place_images
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from blog_agent.nodes.orchestrator import orchestrator_node
from blog_agent.nodes.reducer import decide_images, generate_and_place_images, merge_content
from blog_agent.nodes.research import research_node
from blog_agent.nodes.router import route_next, router_node
from blog_agent.nodes.worker import worker_node
from blog_agent.schemas import State


def fanout(state: State) -> list[Send]:
    """Fan-out: creates one Send per task so workers run in parallel."""
    if state["plan"] is None:
        raise ValueError("fanout: plan is missing. Orchestrator may have failed.")
    return [
        Send(
            "worker",
            {
                "task": task.model_dump(),
                "topic": state["topic"],
                "mode": state["mode"],
                "as_of": state["as_of"],
                "recency_days": state["recency_days"],
                "plan": state["plan"].model_dump(),
                "evidence": [e.model_dump() for e in state.get("evidence", [])],
            },
        )
        for task in state["plan"].tasks
    ]


# ── Reducer subgraph ──────────────────────────────────────────────────────────
_reducer_graph = StateGraph(State)
_reducer_graph.add_node("merge_content", merge_content)
_reducer_graph.add_node("decide_images", decide_images)
_reducer_graph.add_node("generate_and_place_images", generate_and_place_images)
_reducer_graph.add_edge(START, "merge_content")
_reducer_graph.add_edge("merge_content", "decide_images")
_reducer_graph.add_edge("decide_images", "generate_and_place_images")
_reducer_graph.add_edge("generate_and_place_images", END)
_reducer_subgraph = _reducer_graph.compile()

# ── Main graph ────────────────────────────────────────────────────────────────
_g = StateGraph(State)
_g.add_node("router", router_node)
_g.add_node("research", research_node)
_g.add_node("orchestrator", orchestrator_node)
_g.add_node("worker", worker_node)
_g.add_node("reducer", _reducer_subgraph)

_g.add_edge(START, "router")
_g.add_conditional_edges(
    "router", route_next, {"research": "research", "orchestrator": "orchestrator"}
)
_g.add_edge("research", "orchestrator")
_g.add_conditional_edges("orchestrator", fanout, ["worker"])
_g.add_edge("worker", "reducer")
_g.add_edge("reducer", END)

# Public export — used by bwa_frontend.py and blog_agent/__init__.py
app = _g.compile()
