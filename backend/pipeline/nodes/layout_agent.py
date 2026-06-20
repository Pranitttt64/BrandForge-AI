"""
Layout Agent — BrandForge AI
Decides layout template, visual approach, color application, and
typography mood for all generated assets.
Runs at low temperature — these are deterministic design decisions.

Output stored in state["layout_output"] with keys:
  template, flyer_template, content_density, layout_emphasis,
  color_application, typography_mood, content_hierarchy,
  social_card_layout, email_header_style, brand_category_tag
"""

from __future__ import annotations

from typing import Any

from job_manager import job_manager


# ---------------------------------------------------------------------------
# Valid values — enforced during normalisation
# ---------------------------------------------------------------------------

VALID_TEMPLATES       = {"hero_left", "minimal_text"}
VALID_DENSITY         = {"low", "medium", "high"}
VALID_EMPHASIS        = {"headline", "image", "data", "cta", "brand_name"}
VALID_COLOR_APP       = {"full-bleed", "accent", "gradient", "monochrome"}
VALID_TYPOGRAPHY      = {"geometric", "humanist", "slab", "display", "mono"}
VALID_SOCIAL_LAYOUT   = {"centered", "left-aligned", "split", "minimal"}
VALID_EMAIL_HEADER    = {"bold-color", "subtle-gradient", "minimal-line", "full-bleed"}
VALID_CATEGORY_TAGS   = {
    "SaaS", "Fintech", "E-commerce", "Health", "Education",
    "Agency", "Retail", "NGO", "Food", "Other",
}


# ---------------------------------------------------------------------------
# Decision rules — map brand signals to layout decisions
# ---------------------------------------------------------------------------

# visual_style → template
STYLE_TO_TEMPLATE: dict[str, str] = {
    "minimal":        "minimal_text",
    "bold-geometric": "hero_left",
    "editorial":      "hero_left",
    "corporate":      "minimal_text",
    "playful":        "hero_left",
    "dark-tech":      "minimal_text",
    "warm-organic":   "hero_left",
    "luxury-clean":   "minimal_text",
}

# brand_tone → typography mood
TONE_TO_TYPOGRAPHY: dict[str, str] = {
    "bold":         "display",
    "friendly":     "humanist",
    "professional": "geometric",
    "playful":      "display",
    "luxury":       "slab",
    "technical":    "mono",
}

# brand_tone → content density
TONE_TO_DENSITY: dict[str, str] = {
    "bold":         "low",
    "friendly":     "medium",
    "professional": "high",
    "playful":      "low",
    "luxury":       "low",
    "technical":    "high",
}

# brand_tone → color application
TONE_TO_COLOR_APP: dict[str, str] = {
    "bold":         "full-bleed",
    "friendly":     "accent",
    "professional": "accent",
    "playful":      "full-bleed",
    "luxury":       "monochrome",
    "technical":    "accent",
}

# brand_tone → email header style
TONE_TO_EMAIL_HEADER: dict[str, str] = {
    "bold":         "bold-color",
    "friendly":     "bold-color",
    "professional": "minimal-line",
    "playful":      "bold-color",
    "luxury":       "full-bleed",
    "technical":    "minimal-line",
}

# brand_category keywords → category tag
CATEGORY_KEYWORD_MAP: list[tuple[str, str]] = [
    ("payment", "Fintech"),
    ("fintech", "Fintech"),
    ("finance", "Fintech"),
    ("banking", "Fintech"),
    ("saas",    "SaaS"),
    ("software","SaaS"),
    ("platform","SaaS"),
    ("health",  "Health"),
    ("medical", "Health"),
    ("fitness", "Health"),
    ("educat",  "Education"),
    ("learn",   "Education"),
    ("course",  "Education"),
    ("shop",    "E-commerce"),
    ("store",   "E-commerce"),
    ("ecommerce","E-commerce"),
    ("retail",  "Retail"),
    ("food",    "Food"),
    ("restaurant","Food"),
    ("agency",  "Agency"),
    ("studio",  "Agency"),
    ("ngo",     "NGO"),
    ("nonprofit","NGO"),
    ("charity", "NGO"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _profile_value(state: dict, key: str, fallback: Any = None) -> Any:
    """Read from top-level state first, then brand_profile fallback."""
    profile = state.get("brand_profile", {}) or {}
    value = state.get(key)
    if value not in (None, "", []):
        return value
    return profile.get(key, fallback)


def _normalise_template(raw: str) -> str:
    """Convert any template name variant to a valid internal name."""
    if not raw:
        return "hero_left"
    clean = str(raw).lower().strip().replace("-", "_").replace(" ", "_")
    if "minimal" in clean:
        return "minimal_text"
    if "hero" in clean:
        return "hero_left"
    return "hero_left"  # safe default


def _infer_category_tag(brand_category: str) -> str:
    """Map brand_category string to one of the valid category tags."""
    lower = (brand_category or "").lower()
    for keyword, tag in CATEGORY_KEYWORD_MAP:
        if keyword in lower:
            return tag
    return "Other"


def _build_deterministic_layout(
    brand_name: str,
    brand_tone: str,
    visual_style: str,
    brand_archetype: str,
    brand_category: str,
    pricing_model: str,
) -> dict:
    """
    Build a fully reasoned layout decision without LLM.
    Used as fallback AND to validate/patch LLM output.
    All decisions are rule-based on brand signals.
    """
    template      = STYLE_TO_TEMPLATE.get(visual_style, "hero_left")
    typography    = TONE_TO_TYPOGRAPHY.get(brand_tone, "geometric")
    density       = TONE_TO_DENSITY.get(brand_tone, "medium")
    color_app     = TONE_TO_COLOR_APP.get(brand_tone, "accent")
    email_header  = TONE_TO_EMAIL_HEADER.get(brand_tone, "bold-color")
    category_tag  = _infer_category_tag(brand_category)

    # Layout emphasis based on archetype
    archetype_emphasis: dict[str, str] = {
        "Hero":      "headline",
        "Sage":      "data",
        "Creator":   "image",
        "Ruler":     "brand_name",
        "Caregiver": "headline",
        "Explorer":  "image",
        "Jester":    "headline",
        "Magician":  "cta",
        "Outlaw":    "headline",
        "Everyman":  "headline",
        "Innocent":  "image",
        "Lover":     "image",
    }
    emphasis = archetype_emphasis.get(brand_archetype, "headline")

    # Social card layout
    social_layout_map: dict[str, str] = {
        "low":    "centered",
        "medium": "left-aligned",
        "high":   "split",
    }
    social_layout = social_layout_map.get(density, "left-aligned")

    # Content hierarchy — what appears most prominently
    hierarchy_map: dict[str, list[str]] = {
        "bold":         ["headline", "value proposition", "CTA"],
        "friendly":     ["headline", "benefit statement", "social proof"],
        "professional": ["brand credibility", "key metrics", "CTA"],
        "playful":      ["headline", "visual hook", "CTA"],
        "luxury":       ["brand name", "tagline", "single CTA"],
        "technical":    ["feature list", "specifications", "CTA"],
    }
    hierarchy = hierarchy_map.get(brand_tone, ["headline", "value proposition", "CTA"])

    return {
        "template":           template,
        "flyer_template":     template,
        "content_density":    density,
        "layout_emphasis":    emphasis,
        "color_application":  color_app,
        "typography_mood":    typography,
        "content_hierarchy":  hierarchy,
        "social_card_layout": social_layout,
        "email_header_style": email_header,
        "brand_category_tag": category_tag,
    }


def _validate_and_patch(
    raw: dict,
    fallback: dict,
) -> dict:
    """
    Validate LLM output against allowed values.
    Patch any missing or invalid field from the rule-based fallback.
    """
    result = dict(raw)

    # template — most critical, normalise first
    raw_template = result.get("template") or result.get("flyer_template", "")
    template = _normalise_template(raw_template)
    result["template"] = template
    result["flyer_template"] = template

    # Validate each field against its allowed set
    validators: dict[str, set[str]] = {
        "content_density":    VALID_DENSITY,
        "layout_emphasis":    VALID_EMPHASIS,
        "color_application":  VALID_COLOR_APP,
        "typography_mood":    VALID_TYPOGRAPHY,
        "social_card_layout": VALID_SOCIAL_LAYOUT,
        "email_header_style": VALID_EMAIL_HEADER,
        "brand_category_tag": VALID_CATEGORY_TAGS,
    }
    for field, valid_set in validators.items():
        val = result.get(field, "")
        if not val or str(val).lower() not in {v.lower() for v in valid_set}:
            result[field] = fallback[field]

    # content_hierarchy must be a non-empty list
    hier = result.get("content_hierarchy", [])
    if not isinstance(hier, list) or not hier:
        result["content_hierarchy"] = fallback["content_hierarchy"]

    return result


# ---------------------------------------------------------------------------
# Main node
# ---------------------------------------------------------------------------

async def layout_node(state: dict) -> dict:
    """
    Decides layout and visual approach for all generated assets.
    Combines LLM judgment with deterministic rule-based validation.
    """
    job_id = state.get("job_id", "unknown")

    job_manager.emit(job_id, {
        "type": "layout_agent",
        "stage": "layout_agent",
        "status": "running",
        "message": "Deciding layout and visual approach...",
    })

    from rag.retriever import query_brand_knowledge
    from llm.client import get_llm
    from llm.prompts import LAYOUT_PROMPT
    from utils import parse_llm_json

    # --- Pull all state values ---
    brand_name      = _profile_value(state, "brand_name", "the brand")
    brand_tone      = _profile_value(state, "brand_tone", "professional")
    target_audience = _profile_value(state, "target_audience", "teams")
    visual_style    = _profile_value(state, "visual_style", "minimal")
    brand_archetype = _profile_value(state, "brand_archetype", "Sage")
    pricing_model   = _profile_value(state, "pricing_model", "unknown")
    brand_category  = _profile_value(state, "brand_category", "Brand")
    collection_id   = state.get("chroma_collection_id", "")

    # --- Build deterministic fallback first ---
    # This is used both as fallback AND to patch invalid LLM output
    deterministic = _build_deterministic_layout(
        brand_name=brand_name,
        brand_tone=brand_tone,
        visual_style=visual_style,
        brand_archetype=brand_archetype,
        brand_category=brand_category,
        pricing_model=pricing_model,
    )

    # --- RAG retrieval ---
    rag_context = ""
    if collection_id:
        try:
            rag_context = query_brand_knowledge(
                collection_id=collection_id,
                question=(
                    f"{brand_name} visual identity brand design aesthetic "
                    f"layout style hero content sections"
                ),
                agent="layout_agent",
                max_chunks=6,
            )
            print(f"[layout_agent] RAG context: {len(rag_context):,} chars")
        except Exception as e:
            print(f"[layout_agent] RAG query failed (non-fatal): {e}")

    # --- Format prompt ---
    prompt = LAYOUT_PROMPT.format(
        brand_name=brand_name,
        brand_tone=brand_tone,
        target_audience=target_audience,
        visual_style=visual_style,
        brand_archetype=brand_archetype,
        pricing_model=pricing_model,
        brand_category=brand_category,
        rag_context=rag_context[:4000] if rag_context else "No additional context.",
    )

    # --- LLM call (low temperature — design decisions should be consistent) ---
    layout_output: dict = {}
    llm = get_llm(temperature=0.25)

    try:
        response = await llm.ainvoke(prompt)
        raw_content = (
            response.content
            if hasattr(response, "content")
            else str(response)
        )
        parsed = parse_llm_json(raw_content)

        if not parsed or not isinstance(parsed, dict):
            raise ValueError("LLM returned empty or non-dict JSON")

        # Validate and patch with deterministic rules
        layout_output = _validate_and_patch(parsed, deterministic)

        print(
            f"[layout_agent] LLM decision — "
            f"template={layout_output['template']} | "
            f"density={layout_output['content_density']} | "
            f"typography={layout_output['typography_mood']}"
        )

    except Exception as e:
        print(
            f"[layout_agent] LLM/parse error (using deterministic layout): {e}"
        )
        layout_output = deterministic

    print(
        f"[layout_agent] Final layout — "
        f"template={layout_output['template']} | "
        f"color={layout_output['color_application']} | "
        f"category={layout_output['brand_category_tag']}"
    )

    event = {
        "type": "layout_agent",
        "stage": "layout_agent",
        "status": "done",
        "message": (
            f"Layout decided — "
            f"template: {layout_output['template']} | "
            f"density: {layout_output['content_density']} | "
            f"typography: {layout_output['typography_mood']}"
        ),
    }
    job_manager.emit(job_id, event)

    return {"layout_output": layout_output, "events": [event]}