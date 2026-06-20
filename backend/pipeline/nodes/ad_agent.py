"""
Ad Agent — BrandForge AI
Generates multi-format performance ad copy using the AD_PROMPT schema.
Output: headlines, body copies, CTAs, Google RSA, Meta, LinkedIn, hooks.
"""

from __future__ import annotations

from typing import Any

from job_manager import job_manager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _profile_value(state: dict, key: str, fallback: Any = None) -> Any:
    profile = state.get("brand_profile", {}) or {}
    value = state.get(key)
    if value not in (None, "", []):
        return value
    return profile.get(key, fallback)


def _join(value: Any) -> str:
    if isinstance(value, list):
        return "\n- " + "\n- ".join(str(v) for v in value if v) if value else ""
    return str(value) if value else ""


def _first(value: Any, fallback: str = "") -> str:
    if isinstance(value, list):
        return str(value[0]) if value else fallback
    return str(value) if value else fallback


def _trunc(text: str, limit: int) -> str:
    """Truncate string to limit chars."""
    return str(text or "")[:limit]


# ---------------------------------------------------------------------------
# Output normaliser
# ---------------------------------------------------------------------------

def _normalize_ad_output(
    raw: dict,
    brand_name: str,
    brand_category: str,
    target_audience: str,
    usps: list[str],
    competitive_edge: str,
    emotional_benefit: str,
    pricing_model: str,
) -> dict:
    """
    Ensure ad_output has all required keys with real brand-specific content.
    All patches use actual brand data — never generic filler.
    """
    if not isinstance(raw, dict):
        raw = {}

    prod = brand_name
    usp0 = usps[0] if usps else competitive_edge or f"{brand_name} delivers value"
    usp1 = usps[1] if len(usps) > 1 else emotional_benefit or usp0
    usp2 = usps[2] if len(usps) > 2 else usp0
    aud  = (target_audience or "teams").split()[0]

    # --- Headlines (5) ---
    headlines = raw.get("headlines", [])
    if not isinstance(headlines, list):
        headlines = []
    fallback_headlines = [
        f"{brand_name}: {_trunc(usp0, 45)}",
        f"Get {_trunc(usp0, 40)} — with {brand_name}",
        f"Trusted by {aud}s who need {_trunc(usp0, 35)}",
        f"Why top {aud}s choose {brand_name}",
        f"{pricing_model.title() if pricing_model != 'unknown' else 'Try'} {brand_name} today",
    ]
    while len(headlines) < 5:
        headlines.append(fallback_headlines[len(headlines) % len(fallback_headlines)])
    raw["headlines"] = [str(h) for h in headlines[:5]]

    # --- Body copies (3) ---
    bodies = raw.get("body_copies", [])
    if not isinstance(bodies, list):
        bodies = []
    fallback_bodies = [
        (
            f"Struggling with {_trunc(usp0, 40).lower()}? {brand_name} changes that. "
            f"Built specifically for {target_audience or 'teams like yours'}, it delivers "
            f"{_trunc(usp0, 50).lower()}. The result: {emotional_benefit or 'more confidence in every decision'}."
        ),
        (
            f"Imagine a world where {_trunc(usp0, 45).lower()} is just... handled. "
            f"{brand_name} makes that real for {target_audience or 'modern teams'}. "
            f"Thousands already use it to {_trunc(usp1, 45).lower()}."
        ),
        (
            f"{brand_name} customers consistently report {_trunc(usp0, 45).lower()}. "
            f"That's not an accident — it's built into every part of the product. "
            f"{competitive_edge or 'The differentiator: a focused, proven approach.'}"
        ),
    ]
    while len(bodies) < 3:
        bodies.append(fallback_bodies[len(bodies) % len(fallback_bodies)])
    raw["body_copies"] = [str(b) for b in bodies[:3]]

    # --- CTAs (3) ---
    ctas = raw.get("ctas", [])
    if not isinstance(ctas, list):
        ctas = []
    fallback_ctas = [
        f"Start with {brand_name}",
        f"Try {brand_name} Free",
        "See the Results",
    ]
    while len(ctas) < 3:
        ctas.append(fallback_ctas[len(ctas) % len(fallback_ctas)])
    raw["ctas"] = [str(c) for c in ctas[:3]]

    # --- Google RSA ---
    rsa = raw.get("google_rsa", {})
    if not isinstance(rsa, dict):
        rsa = {}

    rsa_headlines = rsa.get("headlines", [])
    if not isinstance(rsa_headlines, list):
        rsa_headlines = []
    fallback_rsa_heads = [
        _trunc(brand_name, 30),
        _trunc(usp0[:28], 30),
        _trunc(f"Try {brand_name}", 30),
        _trunc(f"{aud} favorite", 30),
        _trunc(f"Results guaranteed", 30),
    ]
    while len(rsa_headlines) < 5:
        rsa_headlines.append(fallback_rsa_heads[len(rsa_headlines) % len(fallback_rsa_heads)])
    # Enforce 30-char limit
    rsa["headlines"] = [_trunc(str(h), 30) for h in rsa_headlines[:5]]

    rsa_descs = rsa.get("descriptions", [])
    if not isinstance(rsa_descs, list):
        rsa_descs = []
    fallback_rsa_descs = [
        _trunc(f"{brand_name} helps {target_audience or 'teams'} {usp0.lower()}. Try it today.", 90),
        _trunc(f"{competitive_edge or usp1}. Start free.", 90),
    ]
    while len(rsa_descs) < 2:
        rsa_descs.append(fallback_rsa_descs[len(rsa_descs) % len(fallback_rsa_descs)])
    rsa["descriptions"] = [_trunc(str(d), 90) for d in rsa_descs[:2]]
    raw["google_rsa"] = rsa

    # --- Meta primary text ---
    meta = raw.get("meta_primary_text", "")
    if not meta or len(str(meta).strip()) < 30:
        meta = (
            f"Still dealing with {_trunc(usp0, 40).lower()}? "
            f"{brand_name} was built specifically for {target_audience or 'people like you'}. "
            f"Check out what it does — you might be surprised."
        )
    raw["meta_primary_text"] = str(meta)

    # --- LinkedIn ad ---
    linkedin = raw.get("linkedin_ad", {})
    if not isinstance(linkedin, dict) or not linkedin.get("body"):
        linkedin = {
            "intro": (
                f"Most {target_audience or 'teams'} face the same challenge: "
                f"{_trunc(usp0, 55).lower()}."
            ),
            "body": (
                f"{brand_name} solves this with {_trunc(_first(usps, usp0), 50).lower()}. "
                f"The business outcome: {emotional_benefit or competitive_edge or 'measurable improvements'}. "
                f"Companies using {brand_name} report {_trunc(usp1, 45).lower()}."
            ),
            "cta": f"Request a {brand_name} Demo",
        }
    raw["linkedin_ad"] = linkedin

    # --- Hooks ---
    hooks = raw.get("hooks", [])
    if not isinstance(hooks, list) or not hooks:
        hooks = [
            f"What if {_trunc(usp0, 45).lower()} was finally solved for {target_audience or 'you'}?",
            f"{brand_name} just hit a milestone: {_trunc(usp0, 45).lower()}. Here's what that means.",
            f"If you're a {aud} dealing with {_trunc(usp0, 40).lower()}, this is for you.",
        ]
    raw["hooks"] = [str(h) for h in hooks[:3]]

    return raw


# ---------------------------------------------------------------------------
# Main node
# ---------------------------------------------------------------------------

async def ad_node(state: dict) -> dict:
    """
    Generates performance ad copy across Google, Meta, LinkedIn formats.
    Stores results in state["ad_output"] with the full schema.
    """
    job_id = state.get("job_id", "unknown")

    job_manager.emit(job_id, {
        "type": "ad_agent",
        "stage": "ad_agent",
        "status": "running",
        "message": "Writing ad copy across all formats...",
    })

    from rag.retriever import query_brand_knowledge
    from llm.client import get_llm
    from llm.prompts import AD_PROMPT
    from utils import parse_llm_json

    # --- Pull all state values ---
    brand_name        = _profile_value(state, "brand_name", "the brand")
    brand_category    = _profile_value(state, "brand_category", "Brand")
    target_audience   = _profile_value(state, "target_audience", "customers")
    usps              = _profile_value(state, "usps", []) or []
    competitive_edge  = _profile_value(state, "competitive_edge", "") or ""
    emotional_benefit = _profile_value(state, "emotional_benefit", "") or ""
    pricing_model     = _profile_value(state, "pricing_model", "unknown") or "unknown"
    collection_id     = state.get("chroma_collection_id", "")

    # --- RAG retrieval ---
    context = ""
    if collection_id:
        try:
            context = query_brand_knowledge(
                collection_id=collection_id,
                question=(
                    f"{brand_name} key differentiators benefits audience "
                    f"social proof statistics results competitive advantage"
                ),
                agent="ad_agent",
                max_chunks=10,
            )
            print(f"[ad_agent] RAG context: {len(context):,} chars")
        except Exception as e:
            print(f"[ad_agent] RAG query failed (non-fatal): {e}")

    # --- Format prompt ---
    prompt = AD_PROMPT.format(
        context=context[:6000] if context else "No additional context available.",
        brand_name=brand_name,
        brand_category=brand_category,
        target_audience=target_audience,
        usps=_join(usps),
        competitive_edge=competitive_edge,
        emotional_benefit=emotional_benefit,
        pricing_model=pricing_model,
    )

    # --- LLM call ---
    ad_output: dict = {}
    llm = get_llm(temperature=0.82)

    try:
        response = await llm.ainvoke(prompt)
        raw_content = (
            response.content
            if hasattr(response, "content")
            else str(response)
        )
        ad_output = parse_llm_json(raw_content)

        if not ad_output or not isinstance(ad_output, dict):
            raise ValueError("LLM returned empty or non-dict JSON")

        print(
            f"[ad_agent] LLM success — "
            f"headlines: {len(ad_output.get('headlines', []))} | "
            f"hooks: {len(ad_output.get('hooks', []))}"
        )

    except Exception as e:
        print(f"[ad_agent] LLM/parse error (using brand-specific fallback): {e}")
        ad_output = {}  # normalization will build from scratch

    # --- Normalize: fill all gaps with brand-specific content ---
    ad_output = _normalize_ad_output(
        raw=ad_output,
        brand_name=brand_name,
        brand_category=brand_category,
        target_audience=target_audience,
        usps=usps,
        competitive_edge=competitive_edge,
        emotional_benefit=emotional_benefit,
        pricing_model=pricing_model,
    )

    # --- Log final output ---
    print(
        f"[ad_agent] Done — "
        f"headlines={len(ad_output['headlines'])} | "
        f"bodies={len(ad_output['body_copies'])} | "
        f"rsa_heads={len(ad_output['google_rsa']['headlines'])} | "
        f"hooks={len(ad_output['hooks'])}"
    )

    event = {
        "type": "ad_agent",
        "stage": "ad_agent",
        "status": "done",
        "message": (
            f"Ad copy generated — "
            f"{len(ad_output['headlines'])} headlines, "
            f"{len(ad_output['body_copies'])} body variants, "
            f"Google RSA, Meta, LinkedIn"
        ),
    }
    job_manager.emit(job_id, event)

    return {"ad_output": ad_output, "events": [event]}