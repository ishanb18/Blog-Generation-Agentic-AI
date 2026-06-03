"""
blog_agent/nodes/reducer.py — Reducer subgraph nodes.

Three-node pipeline that runs after all workers finish:
    merge_content → decide_images → generate_and_place_images

Includes retry logic (exponential backoff) for Gemini image generation.
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage

from blog_agent.config import GEMINI_IMAGE_MODEL, MAX_IMAGE_RETRIES, llm
from blog_agent.schemas import GlobalImagePlan, State

DECIDE_IMAGES_SYSTEM = """You are an expert technical editor.
Decide if images/diagrams are needed for THIS blog.

Rules:
- Max 3 images total.
- Each image must materially improve understanding (diagram/flow/table-like visual).
- Insert placeholders exactly: [[IMAGE_1]], [[IMAGE_2]], [[IMAGE_3]].
- If no images needed: md_with_placeholders must equal input and images=[].
- Avoid decorative images; prefer technical diagrams with short labels.
Return strictly GlobalImagePlan.
"""


def _safe_slug(title: str) -> str:
    """Converts a blog title into a safe filename slug."""
    s = title.strip().lower()
    s = re.sub(r"[^a-z0-9 _-]+", "", s)
    s = re.sub(r"\s+", "_", s).strip("_")
    return s or "blog"


def _gemini_generate_image_bytes(prompt: str) -> bytes:
    """
    Calls Gemini image generation API and returns raw PNG bytes.

    Raises:
        RuntimeError: If GOOGLE_API_KEY is not set or no image is returned.
    """
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not set.")

    client = genai.Client(api_key=api_key)
    resp = client.models.generate_content(
        model=GEMINI_IMAGE_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            safety_settings=[
                types.SafetySetting(
                    category="HARM_CATEGORY_DANGEROUS_CONTENT",
                    threshold="BLOCK_ONLY_HIGH",
                )
            ],
        ),
    )

    parts = getattr(resp, "parts", None)
    if not parts and getattr(resp, "candidates", None):
        try:
            parts = resp.candidates[0].content.parts
        except Exception:
            parts = None

    if not parts:
        raise RuntimeError("No image content returned (safety/quota/SDK issue).")

    for part in parts:
        inline = getattr(part, "inline_data", None)
        if inline and getattr(inline, "data", None):
            return inline.data

    raise RuntimeError("No inline image bytes found in API response.")


def merge_content(state: State) -> dict:
    """Merges parallel worker sections into a single ordered markdown document."""
    plan = state["plan"]
    if plan is None:
        raise ValueError("merge_content: plan is missing from state.")

    ordered_sections = [
        md for _, md in sorted(state["sections"], key=lambda x: x[0])
    ]
    body = "\n\n".join(ordered_sections).strip()
    merged_md = f"# {plan.blog_title}\n\n{body}\n"
    return {"merged_md": merged_md}


def decide_images(state: State) -> dict:
    """Uses the LLM to decide image placement and generate prompts."""
    plan = state["plan"]
    if plan is None:
        raise ValueError("decide_images: plan is missing from state.")

    planner = llm.with_structured_output(GlobalImagePlan)
    image_plan = planner.invoke([
        SystemMessage(content=DECIDE_IMAGES_SYSTEM),
        HumanMessage(content=(
            f"Blog kind: {plan.blog_kind}\n"
            f"Topic: {state['topic']}\n\n"
            "Insert placeholders + propose image prompts.\n\n"
            f"{state['merged_md']}"
        )),
    ])

    return {
        "md_with_placeholders": image_plan.md_with_placeholders,
        "image_specs": [img.model_dump() for img in image_plan.images],
    }


def generate_and_place_images(state: State) -> dict:
    """
    Generates each image via Gemini (with retry) and replaces placeholders.

    Retries up to MAX_IMAGE_RETRIES times with exponential backoff.
    A failed image never crashes the pipeline — a fallback block is inserted.
    """
    plan = state["plan"]
    if plan is None:
        raise ValueError("generate_and_place_images: plan is missing from state.")

    md = state.get("md_with_placeholders") or state["merged_md"]
    image_specs = state.get("image_specs", []) or []

    if not image_specs:
        Path(f"{_safe_slug(plan.blog_title)}.md").write_text(md, encoding="utf-8")
        return {"final": md}

    images_dir = Path("images")
    images_dir.mkdir(exist_ok=True)

    for spec in image_specs:
        placeholder = spec["placeholder"]
        out_path = images_dir / spec["filename"]

        if not out_path.exists():
            last_error: Optional[Exception] = None
            for attempt in range(1, MAX_IMAGE_RETRIES + 1):
                try:
                    out_path.write_bytes(_gemini_generate_image_bytes(spec["prompt"]))
                    last_error = None
                    break
                except Exception as exc:
                    last_error = exc
                    if attempt < MAX_IMAGE_RETRIES:
                        time.sleep(2 ** attempt)  # 2 s, then 4 s

            if last_error is not None:
                fallback = (
                    f"> **[IMAGE GENERATION FAILED after {MAX_IMAGE_RETRIES} attempts]**"
                    f" {spec.get('caption', '')}\n>\n"
                    f"> **Error:** {last_error}\n"
                )
                md = md.replace(placeholder, fallback)
                continue

        img_md = f"![{spec['alt']}](images/{spec['filename']})\n*{spec['caption']}*"
        md = md.replace(placeholder, img_md)

    Path(f"{_safe_slug(plan.blog_title)}.md").write_text(md, encoding="utf-8")
    return {"final": md}
