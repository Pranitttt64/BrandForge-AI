"""
Critic Node — BrandForge AI
Quality gate before asset generation.
Validates all agent outputs, patches missing/invalid fields using real
brand data from state, and ensures asset_generator receives complete input.

Philosophy:
- Never patch with generic strings. Every patch uses brand_name, usps,
  brand_promise, competitive_edge pulled from state.
- Never block the pipeline. Always set critic_approved = True.
- Log every issue clearly for debugging.
- Guarantee layout_output has all 10 required keys.
- Guarantee copy_output has all 9 required keys with correct sub-structure.
- Guarantee email_output has all 3 email types with all 6 fields each.
"""

from __future__ import annotations

from typing import Any

from job_manager import job_manager


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REQUIRED_COPY_KEYS = {
    "headlines", "hero_text", "subheadlines", "value_props",
    "call_to_actions", "tagline", "elevator_pitch",
    "usp_titles", "usp_descriptions",
}

REQUIRED_COPY_TONE_KEYS = {"bold", "friendly", "professional"}

REQUIRED_EMAIL_TYPES = {
    "email_welcome", "email_promo", "email_reengagement",
}

REQUIRED_EMAIL_FIELDS = {
    "subject", "preview_text", "headline", "body", "cta_text", "ps_line",
}

REQUIRED_LAYOUT_KEYS = {
    "template", "flyer_template", "content_density", "layout_emphasis",
    "color_application", "typography_mood", "content_hierarchy",
    "social_card_layout", "email_header_style", "brand_category_tag",
}

VALID_TEMPLATES = {"hero_left", "minimal_text"}

GENERIC_PHRASES = (
    "thank you for joining",
    "thank you for choosing",
    "thank you for your interest",
    "i hope this email finds you well",
    "welcome to the next generation",
    "discover what's possible",
    "the smarter way to work",
    "enterprise-grade. startup-ready",
    "work better, together",
    "built for what's next",
    "your brand", "our solution",
    "get started", "learn more",
    "click here",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pv(state: dict, key: str, fallback: Any = None) -> Any:
    """Read from top-level state first, then brand_profile."""
    profile = state.get("brand_profile", {}) or {}
    val = state.get(key)
    if val not in (None, "", []):
        return val
    return profile.get(key, fallback)


def _first(value: Any, fallback: str = "") -> str:
    if isinstance(value, list):
        return str(value[0]) if value else fallback
    return str(value) if value else fallback


def _is_generic(text: str) -> bool:
    if not text or len(str(text).strip()) < 5:
        return True
    lower = str(text).lower().strip()
    return any(g in lower for g in GENERIC_PHRASES)


def _is_valid_list(val: Any, min_len: int = 1) -> bool:
    return isinstance(val, list) and len(val) >= min_len and all(
        v and not _is_generic(str(v)) for v in val[:min_len]
    )


def _is_valid_tone_dict(val: Any) -> bool:
    """Check a tone-keyed dict has at least one valid tone with content."""
    if not isinstance(val, dict):
        return False
    return any(
        tone in val and _is_valid_list(val[tone])
        for tone in REQUIRED_COPY_TONE_KEYS
    )


# ---------------------------------------------------------------------------
# Copy output validator / patcher
# ---------------------------------------------------------------------------

def _validate_copy_output(
    copy_output: Any,
    brand_name: str,
    brand_tone: str,
    usps: list[str],
    brand_promise: str,
    target_audience: str,
    competitive_edge: str,
    key_products: list[str],
) -> tuple[dict, list[str]]:
    """
    Validates copy_output against the full COPYWRITER_PROMPT schema.
    Returns (patched_copy_output, list_of_issues_found).
    All patches use real brand data — zero generic strings.
    """
    issues: list[str] = []

    if not isinstance(copy_output, dict):
        issues.append("copy_output is not a dict — full rebuild")
        copy_output = {}

    prod  = _first(key_products, brand_name)
    usp0  = usps[0] if usps else brand_promise or f"{brand_name} delivers value"
    usp1  = usps[1] if len(usps) > 1 else competitive_edge or usp0
    usp2  = usps[2] if len(usps) > 2 else usp0

    # --- headlines ---
    headlines = copy_output.get("headlines", {})
    if not _is_valid_tone_dict(headlines):
        issues.append("headlines: missing or generic tone variants")
        copy_output["headlines"] = {
            "bold": [
                f"{brand_name}: {usp0[:50]}",
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
                f"The proven advantage: {brand_name}",
            ],
        }

    # --- hero_text ---
    hero_text = copy_output.get("hero_text", {})
    if not isinstance(hero_text, dict) or not any(
        hero_text.get(t) and not _is_generic(hero_text.get(t, ""))
        for t in REQUIRED_COPY_TONE_KEYS
    ):
        issues.append("hero_text: missing or generic")
        copy_output["hero_text"] = {
            "bold": brand_promise or f"{brand_name} gives you {usp0.lower()[:60]}.",
            "friendly": f"With {brand_name}, {(target_audience or 'your team').split()[0]} gets {usp0.lower()[:60]}.",
            "professional": f"{brand_name} enables {target_audience or 'teams'} to achieve {usp0.lower()[:60]}.",
        }

    # --- subheadlines ---
    subheadlines = copy_output.get("subheadlines", {})
    if not _is_valid_tone_dict(subheadlines):
        issues.append("subheadlines: missing or invalid")
        copy_output["subheadlines"] = {
            "bold": [usp0, usp1],
            "friendly": [
                f"Get {usp0.lower()[:50]} — built in",
                f"Join teams already using {brand_name}",
            ],
            "professional": [
                f"Proven: {usp0[:50]}",
                f"Designed for {target_audience or 'modern teams'}",
            ],
        }

    # --- value_props ---
    value_props = copy_output.get("value_props", {})
    if not _is_valid_tone_dict(value_props):
        issues.append("value_props: missing or invalid")
        copy_output["value_props"] = {
            "bold":         [usp0, usp1, usp2],
            "friendly":     [
                f"Get {usp0.lower()[:50]}",
                f"Your team gains {usp1.lower()[:50]}",
                f"Feel confident with {brand_name}",
            ],
            "professional": [
                f"Operationally: {usp0[:50]}",
                f"Strategically: {usp1[:50]}",
                f"Risk-reduction: {competitive_edge[:50] if competitive_edge else usp2[:50]}",
            ],
        }

    # --- call_to_actions ---
    ctas = copy_output.get("call_to_actions", {})
    if not _is_valid_tone_dict(ctas):
        issues.append("call_to_actions: missing or invalid")
        copy_output["call_to_actions"] = {
            "bold":         [f"Start with {brand_name}", "Get Results Now", "See the Difference"],
            "friendly":     ["Let's Get Started", f"Try {brand_name} Free", "Explore What Fits"],
            "professional": ["Request a Demo", "Schedule a Consultation", "Download the Case Study"],
        }

    # --- tagline ---
    tagline = copy_output.get("tagline", "")
    if not tagline or _is_generic(tagline) or len(tagline.split()) > 9:
        issues.append(f"tagline: missing or generic (was: '{tagline[:40]}')")
        copy_output["tagline"] = (
            brand_promise[:60]
            if brand_promise and not _is_generic(brand_promise) and len(brand_promise.split()) <= 7
            else f"{brand_name}. Built for what matters."
        )

    # --- elevator_pitch ---
    pitch = copy_output.get("elevator_pitch", "")
    if not pitch or _is_generic(pitch) or len(pitch) < 50:
        issues.append("elevator_pitch: missing or too short")
        copy_output["elevator_pitch"] = (
            f"{brand_name} is a {brand_name} solution for "
            f"{target_audience or 'modern teams'}. "
            f"It delivers {usp0.lower()[:60]}. "
            f"The key differentiator: {competitive_edge[:60] if competitive_edge else 'a focused, customer-first approach'}."
        )

    # --- usp_titles ---
    usp_titles = copy_output.get("usp_titles", [])
    if not _is_valid_list(usp_titles, 3):
        issues.append("usp_titles: missing or insufficient")
        copy_output["usp_titles"] = [
            " ".join(u.split()[:5]) for u in (usps[:3] or [f"{brand_name} Value"])
        ]
        while len(copy_output["usp_titles"]) < 3:
            copy_output["usp_titles"].append(f"{brand_name} Advantage {len(copy_output['usp_titles']) + 1}")

    # --- usp_descriptions ---
    usp_descs = copy_output.get("usp_descriptions", [])
    if not _is_valid_list(usp_descs, 3):
        issues.append("usp_descriptions: missing or insufficient")
        copy_output["usp_descriptions"] = list(usps[:3]) if len(usps) >= 3 else (
            usps + [f"{brand_name} delivers quality."] * (3 - len(usps))
        )

    return copy_output, issues


# ---------------------------------------------------------------------------
# Email output validator / patcher
# ---------------------------------------------------------------------------

def _validate_email_output(
    email_output: Any,
    brand_name: str,
    usps: list[str],
    brand_promise: str,
    key_products: list[str],
    target_audience: str,
    emotional_benefit: str,
) -> tuple[dict, list[str]]:
    """
    Validates email_output against the new keyed schema.
    Expects: {email_welcome: {...}, email_promo: {...}, email_reengagement: {...}}
    Each with: subject, preview_text, headline, body, cta_text, ps_line
    """
    issues: list[str] = []

    prod  = _first(key_products, brand_name)
    usp0  = usps[0] if usps else brand_promise or f"{brand_name} core value"
    usp1  = usps[1] if len(usps) > 1 else usp0
    aud   = target_audience or "your team"

    # Fallback content — brand-specific, no generic strings
    FALLBACKS: dict[str, dict[str, str]] = {
        "email_welcome": {
            "subject":      f"You're in — here's where to start with {brand_name}",
            "preview_text": f"One quick tip to get the most out of {prod}",
            "headline":     f"Welcome to {brand_name} — let's get you started",
            "body": (
                f"You made a great choice joining {brand_name}. "
                f"We built this for {aud} who need {usp0.lower()[:60]}. "
                f"Your first step: explore {prod} and see how it fits your workflow. "
                f"Most people who use {brand_name} regularly say it helps them "
                f"{emotional_benefit.lower()[:60] if emotional_benefit else 'work with more confidence'}. "
                f"We'll be right here as you get started."
            ),
            "cta_text": f"Explore {prod}",
            "ps_line":  f"PS: {brand_name} works best when you {usp1.lower()[:60]}.",
        },
        "email_promo": {
            "subject":      f"{brand_name}: unlock {prod} this week",
            "preview_text": f"Here's what {aud.split()[0]} are getting right now",
            "headline":     f"Make the most of {brand_name} — starting today",
            "body": (
                f"Right now is a great moment to go deeper with {brand_name}. "
                f"You get {usp0.lower()[:60]} — something that typically takes "
                f"{aud} a lot longer without the right tool. "
                f"With {prod}, the outcome is clear: {brand_promise.lower()[:60] if brand_promise else usp0.lower()[:60]}. "
                f"Teams who commit to {brand_name} see results faster than they expect. "
                f"Take the next step today."
            ),
            "cta_text": f"Get More from {brand_name}",
            "ps_line":  f"PS: {usp1[:80] if usp1 else f'{brand_name} support is ready to help.'}",
        },
        "email_reengagement": {
            "subject":      f"Still thinking about {brand_name}? Here's what changed",
            "preview_text": f"We've added things you'll actually care about",
            "headline":     f"A lot has happened at {brand_name} since you last visited",
            "body": (
                f"It's been a while — we totally understand. "
                f"Since you last looked at {brand_name}, we've improved {prod} "
                f"in ways that directly affect {aud}. "
                f"The core promise is still the same: {brand_promise.lower()[:60] if brand_promise else usp0.lower()[:60]}. "
                f"Come back for 10 minutes — no pressure, just see if it still fits."
            ),
            "cta_text": f"See What's New at {brand_name}",
            "ps_line":  f"PS: If {brand_name} isn't right for now, just reply — no hard feelings.",
        },
    }

    if not isinstance(email_output, dict):
        issues.append("email_output is not a dict — full rebuild")
        return {k: v for k, v in FALLBACKS.items()}, issues

    result: dict[str, dict] = {}

    for email_key in REQUIRED_EMAIL_TYPES:
        email = email_output.get(email_key, {})
        if not isinstance(email, dict):
            issues.append(f"{email_key}: missing — using brand-specific fallback")
            email = {}

        fallback = FALLBACKS[email_key]
        patched: dict[str, str] = {}

        for field in REQUIRED_EMAIL_FIELDS:
            val = str(email.get(field, "")).strip()
            if not val or _is_generic(val) or (field == "body" and len(val) < 80):
                issues.append(f"{email_key}.{field}: missing or invalid — patched")
                val = fallback[field]
            patched[field] = val

        result[email_key] = patched

    return result, issues


# ---------------------------------------------------------------------------
# Layout output validator / patcher
# ---------------------------------------------------------------------------

def _validate_layout_output(
    layout_output: Any,
    brand_tone: str,
    visual_style: str,
    brand_archetype: str,
    brand_category: str,
) -> tuple[dict, list[str]]:
    """
    Ensures layout_output has all 10 required keys with valid values.
    Builds complete deterministic fallback if LLM output is incomplete.
    """
    issues: list[str] = []

    # Import the deterministic builder from layout_agent
    # This guarantees the critic uses the same logic as the layout node
    try:
        from pipeline.nodes.layout_agent import (
            _build_deterministic_layout,
            _validate_and_patch,
        )
        deterministic = _build_deterministic_layout(
            brand_name="",
            brand_tone=brand_tone,
            visual_style=visual_style,
            brand_archetype=brand_archetype,
            brand_category=brand_category,
            pricing_model="unknown",
        )
    except ImportError:
        # Fallback if layout_agent import fails
        deterministic = {
            "template":           "hero_left",
            "flyer_template":     "hero_left",
            "content_density":    "medium",
            "layout_emphasis":    "headline",
            "color_application":  "accent",
            "typography_mood":    "geometric",
            "content_hierarchy":  ["headline", "value proposition", "CTA"],
            "social_card_layout": "left-aligned",
            "email_header_style": "bold-color",
            "brand_category_tag": "Other",
        }

    if not isinstance(layout_output, dict) or not layout_output:
        issues.append("layout_output: missing or empty — using deterministic layout")
        return deterministic, issues

    # Normalise template
    raw_template = layout_output.get("template") or layout_output.get("flyer_template", "")
    clean = str(raw_template).lower().strip().replace("-", "_").replace(" ", "_")
    if "minimal" in clean:
        template = "minimal_text"
    elif "hero" in clean:
        template = "hero_left"
    else:
        issues.append(f"layout template '{raw_template}' unrecognised — defaulting to hero_left")
        template = "hero_left"

    layout_output["template"] = template
    layout_output["flyer_template"] = template

    # Check all required keys exist with non-empty values
    for key in REQUIRED_LAYOUT_KEYS:
        if not layout_output.get(key):
            issues.append(f"layout_output.{key}: missing — patched from deterministic")
            layout_output[key] = deterministic[key]

    # Ensure content_hierarchy is a list
    hier = layout_output.get("content_hierarchy", [])
    if not isinstance(hier, list) or not hier:
        issues.append("layout_output.content_hierarchy: invalid — patched")
        layout_output["content_hierarchy"] = deterministic["content_hierarchy"]

    return layout_output, issues


# ---------------------------------------------------------------------------
# Main node
# ---------------------------------------------------------------------------

def critic_node(state: dict) -> dict:
    """
    Validates all agent outputs before asset generation.
    Patches any missing, invalid, or generic content using brand data.
    Never blocks the pipeline — always sets critic_approved = True.
    """
    job_id = state.get("job_id", "unknown")

    job_manager.emit(job_id, {
        "type": "critic",
        "stage": "critic",
        "status": "running",
        "message": "Quality-checking all agent outputs...",
    })

    # --- Pull brand data for intelligent patching ---
    brand_name        = _pv(state, "brand_name", "Brand")
    brand_tone        = _pv(state, "brand_tone", "professional")
    visual_style      = _pv(state, "visual_style", "minimal")
    brand_archetype   = _pv(state, "brand_archetype", "Sage")
    brand_category    = _pv(state, "brand_category", "Brand")
    target_audience   = _pv(state, "target_audience", "customers")
    usps              = _pv(state, "usps", []) or []
    brand_promise     = _pv(state, "brand_promise", "") or ""
    competitive_edge  = _pv(state, "competitive_edge", "") or ""
    emotional_benefit = _pv(state, "emotional_benefit", "") or ""
    key_products      = _pv(state, "key_products_services", []) or []

    all_issues: list[str] = []

    # --- Validate copy_output ---
    copy_output, copy_issues = _validate_copy_output(
        copy_output=state.get("copy_output", {}),
        brand_name=brand_name,
        brand_tone=brand_tone,
        usps=usps,
        brand_promise=brand_promise,
        target_audience=target_audience,
        competitive_edge=competitive_edge,
        key_products=key_products,
    )
    all_issues.extend([f"[copy] {i}" for i in copy_issues])

    # --- Validate email_output ---
    email_output, email_issues = _validate_email_output(
        email_output=state.get("email_output", {}),
        brand_name=brand_name,
        usps=usps,
        brand_promise=brand_promise,
        key_products=key_products,
        target_audience=target_audience,
        emotional_benefit=emotional_benefit,
    )
    all_issues.extend([f"[email] {i}" for i in email_issues])

    # --- Validate layout_output ---
    layout_output, layout_issues = _validate_layout_output(
        layout_output=state.get("layout_output", {}),
        brand_tone=brand_tone,
        visual_style=visual_style,
        brand_archetype=brand_archetype,
        brand_category=brand_category,
    )
    all_issues.extend([f"[layout] {i}" for i in layout_issues])

    # --- Log results ---
    if all_issues:
        print(f"[critic] {len(all_issues)} issue(s) found and patched:")
        for issue in all_issues:
            print(f"[critic]   ✗ {issue}")
    else:
        print("[critic] ✓ All outputs validated — no issues found")

    status  = "patched" if all_issues else "approved"
    message = (
        f"{len(all_issues)} issue(s) patched before asset generation"
        if all_issues
        else "All outputs validated and approved"
    )

    event = {
        "type":    "critic",
        "stage":   "critic",
        "status":  "done",
        "message": message,
    }
    job_manager.emit(job_id, event)

    return {
        "copy_output":      copy_output,
        "email_output":     email_output,
        "layout_output":    layout_output,
        "critic_approved":  True,
        "critic_feedback":  {
            "status":       status,
            "issues":       all_issues,
            "issue_count":  len(all_issues),
        },
        "events": [event],
    }