"""
Copywriter Agent — BrandForge AI
Generates all marketing copy variants using the COPYWRITER_PROMPT schema.
Produces headlines, hero text, subheadlines, value props, CTAs, tagline,
elevator pitch, USP titles and descriptions across 3 tones.
"""

from __future__ import annotations

import re
from typing import Any

from job_manager import job_manager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _profile_value(state: dict, key: str, fallback: Any = None) -> Any:
    """Read a value from top-level state first, then brand_profile fallback."""
    profile = state.get("brand_profile", {}) or {}
    value = state.get(key)
    if value not in (None, "", []):
        return value
    return profile.get(key, fallback)


def _join(value: Any, separator: str = "\n- ") -> str:
    """Safely join a list to a string, or return the string as-is."""
    if isinstance(value, list):
        if not value:
            return ""
        return separator + separator.join(str(v) for v in value if v)
    return str(value) if value else ""


def _pick(d: dict, *keys: str, fallback: Any = None) -> Any:
    """Safely pick the first non-empty value from a dict by ordered keys."""
    for key in keys:
        val = d.get(key)
        if val not in (None, "", [], {}):
            return val
    return fallback


def _pick_tone(d: dict, tone: str) -> Any:
    """
    Pick a value from a tone-keyed dict using a priority cascade.
    If the requested tone is missing, fall back to any available tone.
    """
    if not isinstance(d, dict):
        return d
    priority = [tone, "bold", "professional", "friendly"]
    for t in priority:
        val = d.get(t)
        if val not in (None, "", [], {}):
            return val
    # Last resort: return first available value
    for val in d.values():
        if val not in (None, "", [], {}):
            return val
    return None


def _first(value: Any) -> str:
    """Return first item if list, or the value itself if string."""
    if isinstance(value, list):
        return str(value[0]) if value else ""
    return str(value) if value else ""


def _is_generic(text: str) -> bool:
    """Detect placeholder or banned generic copy."""
    if not text:
        return True
    banned = (
        "discover what's possible",
        "your brand", "our solution", "company name",
        "placeholder", "lorem ipsum", "insert here", "tbd", "todo",
        "the future of", "all-in-one platform", "game-changer",
        "empowering businesses", "we're on a mission",
    )
    lower = text.lower()
    return any(b in lower for b in banned)


# ---------------------------------------------------------------------------
# Output normaliser
# ---------------------------------------------------------------------------

def _normalize_copy_output(
    raw: dict,
    brand_name: str,
    brand_tone: str,
    usps: list[str],
    brand_promise: str,
    target_audience: str,
    competitive_edge: str,
    key_products: list[str],
) -> dict:
    """
    Ensure the copy_output dict has all required keys with non-generic values.
    Patches missing or generic fields using brand data — never uses hardcoded
    generic strings.
    """

    def _safe_headline(tone: str, idx: int) -> str:
        """Build a brand-specific fallback headline."""
        usp = usps[idx % len(usps)] if usps else brand_promise
        templates = {
            "bold": [
                f"{brand_name}: {usps[0] if usps else 'Built Different'}",
                f"Stop Settling. {brand_name} Delivers.",
                f"{_first(key_products) or brand_name} Changes Everything.",
            ],
            "friendly": [
                f"Your {target_audience.split()[0] if target_audience else 'team'} will love {brand_name}",
                f"Meet {brand_name} — built around you",
                f"Everything you need from {brand_name}, nothing you don't",
            ],
            "professional": [
                f"{brand_name}: The {brand_name} Advantage for {target_audience[:30] if target_audience else 'teams'}",
                f"Drive outcomes with {brand_name}'s {_first(key_products) or 'platform'}",
                f"{competitive_edge[:60] if competitive_edge else f'{brand_name} outperforms alternatives'}",
            ],
        }
        options = templates.get(tone, templates["professional"])
        return options[idx % len(options)]

    def _safe_value_prop(tone: str, idx: int) -> str:
        usp = usps[idx % len(usps)] if usps else f"{brand_name} core value"
        return usp

    def _safe_cta(tone: str, idx: int) -> str:
        ctas = {
            "bold": [
                f"Start with {brand_name}",
                "Get Results Now",
                "See the Difference",
            ],
            "friendly": [
                "Let's Get Started",
                f"Try {brand_name} Free",
                "Explore What Fits You",
            ],
            "professional": [
                "Request a Demo",
                "Schedule a Consultation",
                "Download the Case Study",
            ],
        }
        options = ctas.get(tone, ctas["professional"])
        return options[idx % len(options)]

    tones = ["bold", "friendly", "professional"]

    # --- Headlines ---
    headlines = raw.get("headlines", {})
    if not isinstance(headlines, dict):
        headlines = {}
    for tone in tones:
        items = headlines.get(tone, [])
        if not isinstance(items, list):
            items = []
        # Patch missing or generic items (need at least 3)
        while len(items) < 3:
            items.append(_safe_headline(tone, len(items)))
        items = [
            _safe_headline(tone, i) if _is_generic(h) else h
            for i, h in enumerate(items[:3])
        ]
        headlines[tone] = items
    raw["headlines"] = headlines

    # --- Hero text ---
    hero_text = raw.get("hero_text", {})
    if not isinstance(hero_text, dict):
        hero_text = {}
    for tone in tones:
        if not hero_text.get(tone) or _is_generic(hero_text.get(tone, "")):
            hero_text[tone] = (
                brand_promise
                or f"{brand_name} gives {target_audience or 'your team'} "
                   f"the edge they need — starting today."
            )
    raw["hero_text"] = hero_text

    # --- Subheadlines ---
    subheadlines = raw.get("subheadlines", {})
    if not isinstance(subheadlines, dict):
        subheadlines = {}
    for tone in tones:
        items = subheadlines.get(tone, [])
        if not isinstance(items, list):
            items = []
        while len(items) < 2:
            idx = len(items)
            usp = usps[idx % len(usps)] if usps else f"{brand_name} value"
            items.append(usp)
        subheadlines[tone] = items[:2]
    raw["subheadlines"] = subheadlines

    # --- Value props ---
    value_props = raw.get("value_props", {})
    if not isinstance(value_props, dict):
        value_props = {}
    for tone in tones:
        items = value_props.get(tone, [])
        if not isinstance(items, list):
            items = []
        while len(items) < 3:
            items.append(_safe_value_prop(tone, len(items)))
        items = [
            _safe_value_prop(tone, i) if _is_generic(v) else v
            for i, v in enumerate(items[:3])
        ]
        value_props[tone] = items
    raw["value_props"] = value_props

    # --- CTAs ---
    ctas = raw.get("call_to_actions", {})
    if not isinstance(ctas, dict):
        ctas = {}
    for tone in tones:
        items = ctas.get(tone, [])
        if not isinstance(items, list):
            items = []
        while len(items) < 3:
            items.append(_safe_cta(tone, len(items)))
        ctas[tone] = items[:3]
    raw["call_to_actions"] = ctas

    # --- Tagline ---
    tagline = raw.get("tagline", "")
    if not tagline or _is_generic(tagline) or len(tagline.split()) > 9:
        raw["tagline"] = (
            brand_promise[:60]
            if brand_promise and not _is_generic(brand_promise)
            else f"{brand_name}. Built for what matters."
        )

    # ---------------------------------------------------------------------------
# ONLY CHANGE: fix the elevator_pitch fallback in _normalize_copy_output
# Replace this block:
# ---------------------------------------------------------------------------

    # --- Elevator pitch ---
    pitch = raw.get("elevator_pitch", "")
    if not pitch or _is_generic(pitch) or len(pitch) < 40:
        top_usp = usps[0] if usps else "delivering real value"
        raw["elevator_pitch"] = (
            f"{brand_name} is a {brand_category} for "        # <-- was brand_name, now brand_category
            f"{target_audience or 'modern teams'}. "
            f"It {top_usp.lower() if top_usp else 'solves key problems'}. "
            f"The key differentiator: {competitive_edge or 'a focused, customer-first approach'}."
        )

    # --- USP titles ---
    usp_titles = raw.get("usp_titles", [])
    if not isinstance(usp_titles, list):
        usp_titles = []
    while len(usp_titles) < 3:
        idx = len(usp_titles)
        usp = usps[idx % len(usps)] if usps else f"{brand_name} Feature {idx + 1}"
        # Make a short title from the USP
        words = usp.split()[:5]
        usp_titles.append(" ".join(words))
    raw["usp_titles"] = usp_titles[:3]

    # --- USP descriptions ---
    usp_descs = raw.get("usp_descriptions", [])
    if not isinstance(usp_descs, list):
        usp_descs = []
    while len(usp_descs) < 3:
        idx = len(usp_descs)
        usp = usps[idx % len(usps)] if usps else f"{brand_name} delivers value."
        usp_descs.append(usp)
    raw["usp_descriptions"] = usp_descs[:3]

    return raw


# ---------------------------------------------------------------------------
# Main node
# ---------------------------------------------------------------------------

async def copywriter_node(state: dict) -> dict:
    """
    Generates all marketing copy for the brand using COPYWRITER_PROMPT.
    Stores results in state["copy_output"] with the full schema.
    """
    job_id = state.get("job_id", "unknown")

    job_manager.emit(job_id, {
        "type": "copywriter",
        "stage": "copywriter",
        "status": "running",
        "message": "Writing brand copy across 3 tones...",
    })

    # Lazy imports to keep module load fast
    from rag.retriever import query_brand_knowledge
    from llm.client import get_llm
    from llm.prompts import COPYWRITER_PROMPT
    from utils import parse_llm_json

    # --- Pull all state values ---
    brand_name        = _profile_value(state, "brand_name", "the brand")
    brand_category    = _profile_value(state, "brand_category", "Brand")
    brand_tone        = _profile_value(state, "brand_tone", "professional")
    target_audience   = _profile_value(state, "target_audience", "teams and individuals")
    usps              = _profile_value(state, "usps", []) or []
    brand_promise     = _profile_value(state, "brand_promise", "") or ""
    key_products      = _profile_value(state, "key_products_services", []) or []
    competitive_edge  = _profile_value(state, "competitive_edge", "") or ""
    emotional_benefit = _profile_value(state, "emotional_benefit", "") or ""
    brand_archetype   = _profile_value(state, "brand_archetype", "Sage") or "Sage"
    brand_voice       = _profile_value(state, "brand_voice_examples", []) or []
    content_themes    = _profile_value(state, "content_themes", []) or []
    collection_id     = state.get("chroma_collection_id", "")

    # --- RAG retrieval — multi-query for rich copywriting context ---
    context = ""
    if collection_id:
        try:
            context = query_brand_knowledge(
                collection_id=collection_id,
                question=(
                    f"{brand_name} key benefits value proposition "
                    f"features products audience results outcomes"
                ),
                agent="copywriter",
                max_chunks=12,
            )
            print(
                f"[copywriter] RAG context: {len(context):,} chars "
                f"from collection {collection_id}"
            )
        except Exception as e:
            print(f"[copywriter] RAG query failed (non-fatal): {e}")

    # --- Format prompt ---
    prompt = COPYWRITER_PROMPT.format(
        context=context[:7000] if context else "No additional context available.",
        brand_name=brand_name,
        brand_category=brand_category,
        brand_tone=brand_tone,
        target_audience=target_audience,
        usps=_join(usps),
        brand_promise=brand_promise,
        key_products_services=_join(key_products),
        competitive_edge=competitive_edge,
        emotional_benefit=emotional_benefit,
        brand_archetype=brand_archetype,
        brand_voice_examples=_join(brand_voice),
        content_themes=_join(content_themes),
    )

    # --- LLM call ---
    copy_output: dict = {}
    llm = get_llm(temperature=0.85)

    try:
        response = await llm.ainvoke(prompt)
        raw_content = (
            response.content
            if hasattr(response, "content")
            else str(response)
        )
        copy_output = parse_llm_json(raw_content)

        if not copy_output or not isinstance(copy_output, dict):
            raise ValueError("LLM returned empty or non-dict JSON")

        print(
            f"[copywriter] LLM success — "
            f"bold headlines: {copy_output.get('headlines', {}).get('bold', ['?'])[:1]}"
        )

    except Exception as e:
        print(f"[copywriter] LLM/parse error (using brand-specific fallback): {e}")
        # Build from real brand data — never generic
        usp0 = usps[0] if usps else brand_promise or f"{brand_name} core offer"
        usp1 = usps[1] if len(usps) > 1 else competitive_edge or usp0
        usp2 = usps[2] if len(usps) > 2 else emotional_benefit or usp0
        prod = _first(key_products) or brand_name

        copy_output = {
            "headlines": {
                "bold": [
                    f"{brand_name}: {usp0[:40]}",
                    f"Stop Settling. {brand_name} Delivers.",
                    f"{prod} — The Edge You Need.",
                ],
                "friendly": [
                    f"Meet {brand_name} — made for {(target_audience or 'you').split()[0]}",
                    f"Your team deserves {brand_name}",
                    f"Everything you need, right inside {brand_name}",
                ],
                "professional": [
                    f"{brand_name}: {usp0[:50]}",
                    f"Measurable outcomes with {prod}",
                    f"The {brand_category} advantage: {brand_name}",
                ],
            },
            "hero_text": {
                "bold": brand_promise or f"{brand_name} gives you {usp0}.",
                "friendly": f"With {brand_name}, {(target_audience or 'your team').split()[0]} finally gets {usp0.lower()}.",
                "professional": f"{brand_name} enables {target_audience or 'teams'} to achieve {usp0.lower()} — with proven results.",
            },
            "subheadlines": {
                "bold": [usp0, usp1],
                "friendly": [
                    f"Get {usp0.lower()} without the complexity",
                    f"Join teams already using {brand_name}",
                ],
                "professional": [
                    f"Proven: {usp0}",
                    f"Designed for {target_audience or 'modern teams'}",
                ],
            },
            "value_props": {
                "bold": [usp0, usp1, usp2],
                "friendly": [
                    f"Get {usp0.lower()} — built in",
                    f"Your team gains {usp1.lower()}",
                    f"Feel confident knowing {usp2.lower()}",
                ],
                "professional": [
                    f"Operationally: {usp0}",
                    f"Strategically: {usp1}",
                    f"Risk-reduction: {competitive_edge or usp2}",
                ],
            },
            "call_to_actions": {
                "bold": [
                    f"Start with {brand_name}",
                    "Get Results Now",
                    "See the Difference",
                ],
                "friendly": [
                    "Let's Get Started",
                    f"Try {brand_name} Free",
                    "Explore What Fits You",
                ],
                "professional": [
                    "Request a Demo",
                    "Schedule a Consultation",
                    "Download the Case Study",
                ],
            },
            "tagline": (
                brand_promise[:60]
                if brand_promise and len(brand_promise.split()) <= 7
                else f"{brand_name}. Built for what matters."
            ),
            "elevator_pitch": (
                f"{brand_name} is a {brand_category} for {target_audience or 'modern teams'}. "
                f"It delivers {usp0.lower()}. "
                f"What sets it apart: {competitive_edge or 'a focused, customer-first approach'}."
            ),
            "usp_titles": [
                " ".join(u.split()[:5]) for u in (usps[:3] or [f"{brand_name} Value"])
            ],
            "usp_descriptions": [
                u for u in (usps[:3] or [f"{brand_name} delivers quality."])
            ],
        }

    # --- Normalize: fill gaps, reject generics, enforce schema ---
    copy_output = _normalize_copy_output(
        raw=copy_output,
        brand_name=brand_name,
        brand_tone=brand_tone,
        usps=usps,
        brand_promise=brand_promise,
        target_audience=target_audience,
        competitive_edge=competitive_edge,
        key_products=key_products,
    )

    event = {
        "type": "copywriter",
        "stage": "copywriter",
        "status": "done",
        "message": (
            f"Copy generated — "
            f"tagline: \"{copy_output.get('tagline', '')}\" | "
            f"bold: \"{_first(copy_output.get('headlines', {}).get('bold', []))}\""
        ),
    }
    job_manager.emit(job_id, event)

    print(f"[copywriter] Done — tagline: {copy_output.get('tagline', '')}")

    return {"copy_output": copy_output, "events": [event]}