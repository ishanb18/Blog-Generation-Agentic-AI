# System Design — Blog Generation Agentic AI

## Overview

This document explains the key architecture decisions behind the Blog Writer Agent (BWA) — a fully autonomous blog writing system built on LangGraph. The goal is not just to explain *what* it does, but *why* it was designed this way.

---

## 1. Why LangGraph Over Plain Function Chaining?

The simplest approach to building a multi-step AI pipeline is to just call functions sequentially:

```python
# Naive approach
decision = router(topic)
evidence = research(decision.queries)
plan = orchestrator(topic, evidence)
sections = [worker(task, plan) for task in plan.tasks]
blog = merge(sections)
```

This works — but it has serious limitations:

| Problem | LangGraph Solution |
|---|---|
| No parallelism — workers run one by one | `Send()` fan-out runs all workers concurrently |
| No shared state — you pass everything manually | `State` TypedDict is managed by the graph |
| No conditional routing — you branch with `if/else` | `add_conditional_edges()` with named branches |
| Hard to debug — no visibility into intermediate steps | Built-in streaming with `graph.stream()` |
| Can't compose pipelines — one flat flow | Subgraphs can be nested and reused |

**Decision:** LangGraph gives us a proper stateful execution engine with built-in parallelism, streaming, and composability — the right tool for a multi-agent pipeline.

---

## 2. The `Send()` Fan-Out Pattern for Parallel Writing

The most impactful performance decision in this project is how the worker agents are dispatched.

### The Problem
A blog has 5–9 sections. If each worker takes ~5 seconds to write a section, sequential execution takes **25–45 seconds** just for the writing phase.

### The Solution — `Send()` Fan-Out
LangGraph's `Send` primitive lets you dispatch multiple copies of a node simultaneously:

```python
def fanout(state: State) -> list[Send]:
    return [
        Send("worker", {"task": task.model_dump(), ...})
        for task in state["plan"].tasks
    ]
```

All workers start at the same time. Total writing time = **time for the slowest single section**, not the sum of all sections. A 5-section blog that took 25s now finishes in ~5s.

### The Reducer Pattern
Because sections arrive out of order (whichever worker finishes first), the `State` uses an `Annotated` reducer to accumulate them:

```python
sections: Annotated[List[tuple[int, str]], operator.add]
```

`merge_content` then sorts by `task.id` to reassemble them in the correct order.

---

## 3. Why a 3-Node Reducer Subgraph?

After all workers finish, the reducer subgraph runs:

```
merge_content → decide_images → generate_and_place_images
```

### Why a Subgraph?
This is a self-contained pipeline with its own internal state flow. Wrapping it as a subgraph means:
- It can be tested independently
- It can be replaced or upgraded without touching the main graph
- The main graph stays clean — one edge: `worker → reducer`

### Why Separate `decide_images` and `generate_and_place_images`?
Image planning and image generation are intentionally split:

- **`decide_images`** — pure LLM call, fast, no side effects. Decides *where* images should go and writes their prompts.
- **`generate_and_place_images`** — expensive API call (Gemini), slow, has side effects (writes files). Isolated so failures here don't affect the planning step.

This separation also makes it easy to add a "dry run" mode later — just skip `generate_and_place_images`.

---

## 4. Why Three Research Modes?

The Router agent outputs one of three modes, each with a different recency window:

| Mode | Recency Window | When Used |
|---|---|---|
| `closed_book` | ~10 years (no cutoff) | Timeless concepts (e.g., "What is a transformer?") |
| `hybrid` | 45 days | Evergreen topics that need current examples/tools |
| `open_book` | 7 days | Breaking news, "latest" releases, weekly roundups |

**Why not always research?** Web search adds 5–15 seconds of latency and costs API quota. For truly evergreen topics (e.g., "explain LSTM"), the LLM's training data is sufficient and more reliable than scraped search results.

**Why structured output for the router?** Using `llm.with_structured_output(RouterDecision)` forces the model to always return a valid `mode` and `needs_research` boolean — no string parsing, no hallucinated values.

---

## 5. Why Mistral AI as the LLM Backbone?

Three reasons:

1. **Free tier** — Mistral offers a generous free API tier, making this project reproducible without a credit card
2. **Strong structured output support** — `mistral-medium-latest` reliably produces valid Pydantic-schema outputs, which the entire pipeline depends on
3. **Speed** — Mistral medium is fast enough that parallel workers don't create timeout issues

**Trade-off:** GPT-4o produces slightly better prose quality but costs significantly more and has stricter rate limits for new accounts.

---

## 6. Why Pydantic v2 for Schemas?

Every agent in the pipeline uses structured output validated by Pydantic models (`Task`, `Plan`, `RouterDecision`, etc.) instead of raw text parsing.

**Without Pydantic:**
```python
# Fragile — LLM output format can drift
response = llm.invoke(prompt).content
plan = json.loads(response)  # crashes if LLM adds extra text
```

**With Pydantic + structured output:**
```python
planner = llm.with_structured_output(Plan)
plan = planner.invoke(messages)  # always a valid Plan object, guaranteed
```

This makes the pipeline **deterministic in structure** even if the content varies — a key requirement for a production-grade system.

---

## 7. Graceful Degradation — The Fallback Philosophy

Every external dependency in this system can fail silently without crashing the pipeline:

| Failure | Behavior |
|---|---|
| `TAVILY_API_KEY` not set | Research skipped; blog written from LLM knowledge |
| `GOOGLE_API_KEY` not set | Images skipped; blog rendered text-only |
| Gemini image generation fails | Retry up to `MAX_IMAGE_RETRIES` times with exponential backoff, then insert a fallback block — blog still usable |
| LLM structured output fails | Exception propagates — only truly unrecoverable failures crash |

**Design principle:** The user always gets a blog. The quality degrades gracefully based on what APIs are available.

---

## 8. Trade-Offs and Limitations

| Decision | Trade-Off |
|---|---|
| Max 3 images per blog | Keeps Gemini API costs low; more images would slow the pipeline significantly |
| Single LLM instance shared across all nodes | Simpler; in production you'd want per-node model selection |
| Blogs saved as `.md` files in the working directory | Simple and portable, but doesn't scale — a production system would use a database |
| Streamlit for UI | Fast to build, great for demos; not suitable for multi-user production deployment |
| No conversation memory across blogs | Each blog is stateless — adding a vector store would enable continuity |

---

## 9. What I Would Do Differently With More Time

1. **Multi-model support** — Let the user choose between GPT-4o, Claude, and Mistral per blog
2. **Vector memory** — Store past blogs in a vector database so the system can reference previous content
3. **PDF / HTML export** — Convert the markdown output to a styled, shareable document
4. **Async execution** — Replace `ThreadPoolExecutor` with `asyncio` for better throughput
5. **Database-backed blog library** — Replace file-based `.md` storage with SQLite or PostgreSQL

---

## 10. Project File Structure

```
blog_agent/                  ← Main Python package
├── config.py                ← All constants + shared LLM instance
├── schemas.py               ← All Pydantic models + State TypedDict
├── utils.py                 ← Shared utilities (slugify, reading time, TOC)
├── graph.py                 ← Assembles and compiles the LangGraph app
└── nodes/
    ├── router.py            ← Topic classification + research mode decision
    ├── research.py          ← Tavily search + evidence synthesis + filtering
    ├── orchestrator.py      ← Structured blog plan generation
    ├── worker.py            ← Single-section writer (runs in parallel)
    └── reducer.py           ← Merge + image planning + image generation

bwa_backend.py               ← Backward-compat shim (re-exports app)
bwa_frontend.py              ← Streamlit UI (streaming, tabs, export)
```
