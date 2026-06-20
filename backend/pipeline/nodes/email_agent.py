"""
Email Agent — BrandForge AI
Generates 3 complete, sendable email campaigns using EMAIL_PROMPT schema.
Output is stored keyed by email type for direct use by asset_generator.
Schema: email_output["email_welcome"], ["email_promo"], ["email_reengagement"]
Each contains: subject, preview_text, headline, body, cta_text, ps_line
"""

from __future__ import annotations

from typing import Any

from job_manager import job_manager


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


def _join(value: Any) -> str:
    """Safely join a list to a bulleted string."""
    if isinstance(value, list):
        if not value:
            return ""
        return "\n- " + "\n- ".join(str(v) for v in value if v)
    return str(value) if value else ""


def _first(value: Any, fallback: str = "") -> str:
    """Return first item if list, or the string itself."""
    if isinstance(value, list):
        return str(value[0]) if value else fallback
    return str(value) if value else fallback


def _is_generic(text: str) -> bool:
    """Detect placeholder or banned generic text."""
    if not text or len(text.strip()) < 5:
        return True
    banned = (
        "your brand", "our solution", "company name",
        "placeholder", "lorem ipsum", "insert here",
        "i hope this email finds you well",
        "thank you for your interest",
        "thank you for choosing",
    )
    lower = text.lower().strip()
    return any(b in lower for b in banned)


# ---------------------------------------------------------------------------
# Email normaliser
# ---------------------------------------------------------------------------

def _normalize_email_output(
    raw: dict,
    brand_name: str,
    brand_tone: str,
    target_audience: str,
    usps: list[str],
    brand_promise: str,
    key_products: list[str],
    emotional_benefit: str,
) -> dict:
    """
    Ensures all 3 email types exist with all required fields populated.
    Input: raw dict from LLM (may have "emails" list or direct keys).
    Output: dict keyed by type — email_welcome, email_promo, email_reengagement.
    """

    prod  = _first(key_products, brand_name)
    usp0  = usps[0] if usps else brand_promise or f"{brand_name} core value"
    usp1  = usps[1] if len(usps) > 1 else usp0
    usp2  = usps[2] if len(usps) > 2 else usp0
    aud   = target_audience or "your team"
    tone_adj = {
        "bold": "direct", "friendly": "warm",
        "professional": "authoritative", "playful": "energetic",
        "luxury": "refined", "technical": "precise",
    }.get(brand_tone, "clear")

    # --- Built-in brand-specific fallbacks per type ---
    FALLBACKS: dict[str, dict] = {
        "email_welcome": {
            "subject": f"You're in — here's where to start with {brand_name}",
            "preview_text": f"One quick tip to get the most out of {prod}",
            "headline": f"Welcome to {brand_name} — let's get you started",
            "body": (
                f"You made a great choice joining {brand_name}. "
                f"We built this for {aud} who need {usp0.lower()}. "
                f"Your first step: explore {prod} and see how it fits your workflow. "
                f"Most people who use {brand_name} regularly say it helps them "
                f"{emotional_benefit.lower() if emotional_benefit else 'work with more confidence'}. "
                f"We'll be right here as you get started — don't hesitate to reach out."
            ),
            "cta_text": f"Explore {prod}",
            "ps_line": (
                f"PS: {brand_name} works best when you {usp1.lower()[:80]}."
                if usp1 else f"PS: Our team is available if you have questions."
            ),
        },
        "email_promo": {
            "subject": f"{brand_name}: unlock {prod} this week",
            "preview_text": f"Here's what {aud} are getting right now",
            "headline": f"Make the most of {brand_name} — starting today",
            "body": (
                f"Right now is a great moment to go deeper with {brand_name}. "
                f"You get {usp0.lower()} — something that typically takes {aud} "
                f"a lot longer to figure out on their own. "
                f"With {prod}, the outcome is clear: {brand_promise.lower() if brand_promise else usp0.lower()}. "
                f"Teams who commit to {brand_name} see results faster than they expect. "
                f"Take the next step today before your momentum slips."
            ),
            "cta_text": f"Get More from {brand_name}",
            "ps_line": (
                f"PS: {usp2[:100] if usp2 else f'{brand_name} has a support team ready to help you.'}"
            ),
        },
        "email_reengagement": {
            "subject": f"Still thinking about {brand_name}? Here's what's changed",
            "preview_text": f"We've added things you'll actually care about",
            "headline": f"A lot has happened at {brand_name} since you last visited",
            "body": (
                f"It's been a while — and we totally understand, life moves fast. "
                f"Since you last looked at {brand_name}, we've improved {prod} "
                f"in ways that directly affect {aud}. "
                f"The core promise is still the same: {brand_promise.lower() if brand_promise else usp0.lower()}. "
                f"If that's still relevant to where you are, we'd love to show you what's new. "
                f"Come back for 10 minutes — no pressure, just see if it still fits."
            ),
            "cta_text": f"See What's New at {brand_name}",
            "ps_line": (
                f"PS: If {brand_name} isn't the right fit right now, "
                f"just reply and let us know — no hard feelings."
            ),
        },
    }

    # --- Parse LLM output ---
    # The LLM returns {"emails": [{type: "welcome", ...}, ...]}
    # We need to convert this to {email_welcome: {...}, email_promo: {...}, ...}

    keyed: dict[str, dict] = {}

    emails_list = raw.get("emails", [])

    # Handle both formats: list under "emails" key, or already keyed
    if isinstance(emails_list, list):
        for email in emails_list:
            if not isinstance(email, dict):
                continue
            email_type = email.get("type", "")
            if email_type == "welcome":
                keyed["email_welcome"] = email
            elif email_type == "promo":
                keyed["email_promo"] = email
            elif email_type in ("reengagement", "re-engagement", "re_engagement"):
                keyed["email_reengagement"] = email
    elif isinstance(raw, dict):
        # Already keyed format
        for k in ("email_welcome", "email_promo", "email_reengagement"):
            if k in raw and isinstance(raw[k], dict):
                keyed[k] = raw[k]

    # --- Ensure all 3 types exist and all fields are filled ---
    REQUIRED_FIELDS = (
        "subject", "preview_text", "headline", "body", "cta_text", "ps_line"
    )

    result: dict[str, dict] = {}

    for email_key, fallback in FALLBACKS.items():
        email = keyed.get(email_key, {})
        if not isinstance(email, dict):
            email = {}

        patched: dict[str, str] = {}
        for field in REQUIRED_FIELDS:
            val = email.get(field, "")
            if not val or _is_generic(str(val)):
                val = fallback.get(field, f"{brand_name} — {field}")
            # Extra validation per field
            if field == "subject" and len(val) > 60:
                val = val[:57] + "..."
            if field == "preview_text" and len(val) > 100:
                val = val[:97] + "..."
            if field == "body" and len(val) < 80:
                val = fallback["body"]
            patched[field] = val

        result[email_key] = patched

    return result


# ---------------------------------------------------------------------------
# Main node
# ---------------------------------------------------------------------------

async def email_node(state: dict) -> dict:
    """
    Generates 3 complete email campaigns for the brand.
    Output stored as state["email_output"] keyed by email type.
    """
    job_id = state.get("job_id", "unknown")

    job_manager.emit(job_id, {
        "type": "email_agent",
        "stage": "email_agent",
        "status": "running",
        "message": "Writing 3 email campaigns...",
    })

    from rag.retriever import query_brand_knowledge
    from llm.client import get_llm
    from llm.prompts import EMAIL_PROMPT
    from utils import parse_llm_json

    # --- Pull all state values ---
    brand_name        = _profile_value(state, "brand_name", "the brand")
    brand_category    = _profile_value(state, "brand_category", "Brand")
    brand_tone        = _profile_value(state, "brand_tone", "professional")
    target_audience   = _profile_value(state, "target_audience", "teams and individuals")
    usps              = _profile_value(state, "usps", []) or []
    brand_promise     = _profile_value(state, "brand_promise", "") or ""
    key_products      = _profile_value(state, "key_products_services", []) or []
    emotional_benefit = _profile_value(state, "emotional_benefit", "") or ""
    brand_voice       = _profile_value(state, "brand_voice_examples", []) or []
    collection_id     = state.get("chroma_collection_id", "")

    # --- RAG retrieval ---
    context = ""
    if collection_id:
        try:
            context = query_brand_knowledge(
                collection_id=collection_id,
                question=(
                    f"{brand_name} welcome onboarding getting started "
                    f"promotional offer re-engagement features benefits "
                    f"customer success trust signals"
                ),
                agent="email_agent",
                max_chunks=10,
            )
            print(
                f"[email_agent] RAG context: {len(context):,} chars"
            )
        except Exception as e:
            print(f"[email_agent] RAG query failed (non-fatal): {e}")

    # --- Format prompt ---
    prompt = EMAIL_PROMPT.format(
        context=context[:7000] if context else "No additional context available.",
        brand_name=brand_name,
        brand_category=brand_category,
        brand_tone=brand_tone,
        target_audience=target_audience,
        usps=_join(usps),
        brand_promise=brand_promise,
        key_products_services=_join(key_products),
        emotional_benefit=emotional_benefit,
        brand_voice_examples=_join(brand_voice),
    )

    # --- LLM call ---
    raw_output: dict = {}
    llm = get_llm(temperature=0.72)

    try:
        response = await llm.ainvoke(prompt)
        raw_content = (
            response.content
            if hasattr(response, "content")
            else str(response)
        )
        raw_output = parse_llm_json(raw_content)

        if not raw_output or not isinstance(raw_output, dict):
            raise ValueError("LLM returned empty or non-dict JSON")

        emails_list = raw_output.get("emails", [])
        print(
            f"[email_agent] LLM success — {len(emails_list)} emails returned"
        )
        for e in emails_list:
            if isinstance(e, dict):
                etype = e.get("type", "?")
                body_len = len(e.get("body", ""))
                print(
                    f"[email_agent]   {etype}: "
                    f"subject='{e.get('subject', '')[:40]}' "
                    f"body={body_len} chars"
                )

    except Exception as e:
        print(f"[email_agent] LLM/parse error (using brand-specific fallback): {e}")
        raw_output = {}

    # --- Normalize: convert list → keyed dict, fill gaps, validate ---
    email_output = _normalize_email_output(
        raw=raw_output,
        brand_name=brand_name,
        brand_tone=brand_tone,
        target_audience=target_audience,
        usps=usps,
        brand_promise=brand_promise,
        key_products=key_products,
        emotional_benefit=emotional_benefit,
    )

    # --- Final validation log ---
    for key, email in email_output.items():
        body_len = len(email.get("body", ""))
        print(
            f"[email_agent] {key}: "
            f"subject='{email.get('subject', '')[:40]}' "
            f"body={body_len} chars "
            f"cta='{email.get('cta_text', '')}'"
        )

    event = {
        "type": "email_agent",
        "stage": "email_agent",
        "status": "done",
        "message": (
            f"3 emails generated — "
            f"welcome: '{email_output.get('email_welcome', {}).get('subject', '')[:35]}'"
        ),
    }
    job_manager.emit(job_id, event)

    return {"email_output": email_output, "events": [event]}