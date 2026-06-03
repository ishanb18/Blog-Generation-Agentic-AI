"""
bwa_backend.py — Backward-compatibility shim.

The logic has been refactored into the `blog_agent/` package:

    blog_agent/
    ├── config.py          # constants + LLM
    ├── schemas.py         # Pydantic models + State
    ├── nodes/
    │   ├── router.py
    │   ├── research.py
    │   ├── orchestrator.py
    │   ├── worker.py
    │   └── reducer.py
    └── graph.py           # builds + exports `app`

This file re-exports `app` so that any code importing from bwa_backend
continues to work without changes.
"""
from blog_agent.graph import app  # noqa: F401
