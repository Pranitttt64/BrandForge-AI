"""
Brand Extractor Node — BrandForge AI
Extracts a rich, multi-field brand profile from scraped content using
color analysis + LLM reasoning. Feeds every downstream agent.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from langchain_core.messages import HumanMessage

from job_manager import job_manager
from llm.client import get_llm
from llm.prompts import BRAND_EXTRACTION_PROMPT
from pipeline.state import BrandForgeState
from rag.retriever import query_brand_knowledge
from utils import parse_llm_json
from utils.colors import extract_brand_colors
from utils.quality import enrich_brand_profile


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Max chars sent to LLM — fits comfortably in Groq llama-3.3-70b context
LLM_CONTEXT_LIMIT = 28000

# Page priority order for content assembly
PAGE_PRIORITY_KEYWORDS = (
    "about", "mission", "story", "features", "product",
    "services", "how", "why", "platform", "solution",
    "pricing", "customers", "home", "index",
)

# Section labels from scraper that carry the most brand signal
HIGH_SIGNAL_SECTION_PREFIXES = (
    "[SOURCE PAGE:",
    "Page title:",
    "OG ",
    "Meta description:",
    "Structured data:",
    "H1 headlines:",
    "H2 subheadings:",
    "Feature/benefit lists:",
    "Brand sections:",
    "Testimonials/Social proof:",
    "Stats & metrics:",
    "Pricing/Plans:",
    "CTAs/Buttons:",
    "Footer content:",
)

MEDIUM_SIGNAL_SECTION_PREFIXES = (
    "H3 sections:",
    "Body text:",
    "Jina reader text:",
    "Dynamic page text:",
)


# ---------------------------------------------------------------------------
# Content assembly helpers
# ---------------------------------------------------------------------------

def _score_page_url(url: str) -> int:
    """
    Lower score = higher priority in context assembly.
    Homepage and about/features pages first, deep blog posts last.
    """
    path = urlparse(url).path.lower().rstrip("/") or "/"
    if path == "/" or path == "":
        return 0
    for i, kw in enumerate(PAGE_PRIORITY_KEYWORDS):
        if kw in path:
            return i + 1
    depth = path.count("/")
    return 50 + depth


def _extract_high_signal_lines(page_text: str, char_budget: int) -> str:
    """
    From a page's full text, extract the most signal-rich lines first
    then fill remaining budget with the rest.
    """
    lines = page_text.splitlines()
    high: list[str] = []
    medium: list[str] = []
    low: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if any(stripped.startswith(p) for p in HIGH_SIGNAL_SECTION_PREFIXES):
            high.append(line)
        elif any(stripped.startswith(p) for p in MEDIUM_SIGNAL_SECTION_PREFIXES):
            medium.append(line)
        else:
            low.append(line)

    # Fill in priority order within budget
    result_lines: list[str] = []
    used = 0
    for group in (high, medium, low):
        for line in group:
            if used + len(line) + 1 > char_budget:
                break
            result_lines.append(line)
            used += len(line) + 1
        if used >= char_budget:
            break

    return "\n".join(result_lines)


def _assemble_llm_context(raw_pages: dict[str, str]) -> str:
    """
    Build the richest possible context string for the LLM within token limits.

    Strategy:
    1. Sort pages by relevance (homepage + core pages first)
    2. For each page, extract high-signal sections first
    3. Fill remaining budget proportionally
    """
    if not raw_pages:
        return ""

    # Sort pages by priority score
    sorted_pages = sorted(raw_pages.items(), key=lambda kv: _score_page_url(kv[0]))

    # Allocate character budget per page
    # Homepage gets 40% of budget, rest split evenly among remaining pages
    n_pages = len(sorted_pages)
    if n_pages == 0:
        return ""

    homepage_budget = int(LLM_CONTEXT_LIMIT * 0.40)
    remaining_budget = LLM_CONTEXT_LIMIT - homepage_budget
    per_page_budget = remaining_budget // max(n_pages - 1, 1) if n_pages > 1 else remaining_budget

    parts: list[str] = []
    total_used = 0

    for i, (page_url, page_text) in enumerate(sorted_pages):
        if total_used >= LLM_CONTEXT_LIMIT:
            break

        budget = homepage_budget if i == 0 else per_page_budget
        available = min(budget, LLM_CONTEXT_LIMIT - total_used)

        if available < 200:
            break

        extracted = _extract_high_signal_lines(page_text, available)
        if not extracted.strip():
            # Fallback: just take first `available` chars of raw text
            extracted = page_text[:available]

        section = f"\n{'='*60}\n[PAGE: {page_url}]\n{'='*60}\n{extracted}"
        parts.append(section)
        total_used += len(section)

    return "\n".join(parts)


def _fallback_brand_name_from_url(url: str) -> str:
    """Extract a best-guess brand name from the URL as last resort."""
    try:
        netloc = urlparse(url).netloc
        # Strip www. and TLD
        name = netloc.removeprefix("www.")
        name = re.sub(r"\.(com|io|co|net|org|app|ai|dev|xyz|me).*$", "", name)
        # Capitalize nicely
        return name.replace("-", " ").replace("_", " ").title()
    except Exception:
        return "Unknown Brand"


def _validate_and_patch_profile(
    profile: dict,
    url: str,
    colors: dict,
) -> dict:
    """
    Ensure all required fields exist and are non-empty.
    Patches missing or placeholder values with smart defaults.
    """
    brand_name = profile.get("brand_name", "").strip()
    if not brand_name or brand_name.lower() in ("unknown", "n/a", "brand", "company"):
        profile["brand_name"] = _fallback_brand_name_from_url(url)

    # Ensure tone is valid
    valid_tones = {"bold", "friendly", "professional", "playful", "luxury", "technical"}
    if profile.get("brand_tone", "").lower() not in valid_tones:
        profile["brand_tone"] = "professional"

    # Ensure USPs list has at least 3 entries
    usps = profile.get("usps", [])
    if not isinstance(usps, list):
        usps = []
    while len(usps) < 3:
        usps.append(f"Quality {profile['brand_name']} experience")
    profile["usps"] = usps[:6]

    # Ensure key_products_services is a list
    kps = profile.get("key_products_services", [])
    if not isinstance(kps, list) or not kps:
        profile["key_products_services"] = [profile["brand_name"]]

    # Ensure brand_voice_examples is a list
    bve = profile.get("brand_voice_examples", [])
    if not isinstance(bve, list) or not bve:
        profile["brand_voice_examples"] = [f"Experience {profile['brand_name']}"]

    # New fields — patch if missing
    if not profile.get("brand_promise"):
        profile["brand_promise"] = (
            f"{profile['brand_name']} gives you everything you need "
            f"to {profile.get('brand_category', 'succeed')}."
        )

    if not profile.get("competitive_edge"):
        profile["competitive_edge"] = (
            f"{profile['brand_name']} stands out through its focused "
            "approach to customer value."
        )

    if not profile.get("emotional_benefit"):
        profile["emotional_benefit"] = (
            "Confidence and clarity in a space that usually feels complex."
        )

    if not profile.get("brand_archetype"):
        profile["brand_archetype"] = "Sage"

    valid_styles = {
        "minimal", "bold-geometric", "editorial", "corporate",
        "playful", "dark-tech", "warm-organic", "luxury-clean",
    }
    if profile.get("visual_style", "").lower() not in valid_styles:
        # Infer from tone
        tone_to_style = {
            "bold": "bold-geometric",
            "friendly": "warm-organic",
            "professional": "corporate",
            "playful": "playful",
            "luxury": "luxury-clean",
            "technical": "dark-tech",
        }
        profile["visual_style"] = tone_to_style.get(
            profile.get("brand_tone", "professional"), "minimal"
        )

    valid_pricing = {
        "free", "freemium", "subscription", "usage-based",
        "enterprise", "one-time", "marketplace", "unknown",
    }
    if profile.get("pricing_model", "").lower() not in valid_pricing:
        profile["pricing_model"] = "unknown"

    # Ensure list fields are actually lists
    for list_field in ("content_themes", "industry_language"):
        val = profile.get(list_field, [])
        if not isinstance(val, list) or not val:
            profile[list_field] = []

    # Strip any placeholder / generic garbage from all string fields
    generic_phrases = (
        "your brand", "our solution", "company name", "placeholder",
        "lorem ipsum", "insert here", "tbd", "todo",
    )
    for key, val in profile.items():
        if isinstance(val, str):
            lower = val.lower()
            if any(gp in lower for gp in generic_phrases):
                profile[key] = ""  # will be re-patched by caller if needed

    return profile


# ---------------------------------------------------------------------------
# Main node
# ---------------------------------------------------------------------------

async def brand_extractor_node(state: BrandForgeState) -> dict:
    job_id = state.get("job_id", "unknown")
    source_url = state.get("url", "")

    job_manager.emit(job_id, {
        "type": "brand_extractor",
        "stage": "brand_extractor",
        "status": "running",
        "message": "Extracting brand identity...",
    })

    raw_pages: dict[str, str] = state.get("raw_pages", {})

    # -------------------------------------------------------------------
    # Step 1: Color extraction (deterministic, runs on all content)
    # -------------------------------------------------------------------
    # Use full combined text for color extraction — more data = better accuracy
    full_combined = "\n".join(raw_pages.values())
    colors = extract_brand_colors(full_combined)

    brand_colors = {
        "primary": colors["primary"],
        "secondary": colors["secondary"],
        "accent": colors["accent"],
        "background": colors["background"],
        "text": colors["text"],
    }

    print(
        f"[brand_extractor] Colors extracted: "
        f"primary={colors['primary']} accent={colors['accent']}"
    )

    # -------------------------------------------------------------------
    # Step 2: Assemble smart LLM context
    # -------------------------------------------------------------------
    llm_context = _assemble_llm_context(raw_pages)

    if not llm_context.strip():
        print(f"[brand_extractor] WARNING: No content to analyze for job {job_id}")
        llm_context = f"Website URL: {source_url}\nNo content could be scraped."

    print(
        f"[brand_extractor] Context assembled: "
        f"{len(llm_context):,} chars from {len(raw_pages)} pages"
    )

    # -------------------------------------------------------------------
    # Step 3: LLM brand profile extraction
    # -------------------------------------------------------------------
    prompt = BRAND_EXTRACTION_PROMPT.format(context=llm_context)
    brand_profile: dict = {}

    try:
        llm = get_llm()
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        raw_response = str(response.content).strip()

        print(f"[brand_extractor] LLM response length: {len(raw_response)} chars")

        brand_profile = parse_llm_json(raw_response)

        if not brand_profile or not isinstance(brand_profile, dict):
            raise ValueError("LLM returned empty or non-dict JSON")

        print(
            f"[brand_extractor] Extracted: {brand_profile.get('brand_name', '?')} | "
            f"tone={brand_profile.get('brand_tone', '?')} | "
            f"archetype={brand_profile.get('brand_archetype', '?')} | "
            f"usps={len(brand_profile.get('usps', []))}"
        )

    except Exception as e:
        print(f"[brand_extractor] LLM extraction failed: {e}")
        # Build a minimal fallback from URL — never use hardcoded brand names
        inferred_name = _fallback_brand_name_from_url(source_url)
        brand_profile = {
            "brand_name": inferred_name,
            "brand_category": "Business",
            "brand_tone": "professional",
            "target_audience": "Customers and prospects exploring this brand online",
            "usps": [
                "Focused on delivering real customer value",
                "Clear and accessible products or services",
                "Built with the customer experience in mind",
            ],
            "brand_promise": f"{inferred_name} delivers quality and clarity.",
            "key_products_services": [inferred_name],
            "competitive_edge": f"{inferred_name} offers a focused, customer-first approach.",
            "brand_voice_examples": [f"Welcome to {inferred_name}"],
            "content_themes": [],
            "emotional_benefit": "Confidence that you made the right choice.",
            "industry_language": [],
            "visual_style": "minimal",
            "pricing_model": "unknown",
            "brand_archetype": "Sage",
            "brand_colors": [],
        }

    # -------------------------------------------------------------------
    # Step 4: Validate and patch all fields
    # -------------------------------------------------------------------
    brand_profile = _validate_and_patch_profile(brand_profile, source_url, colors)

    # -------------------------------------------------------------------
    # Step 5: Enrich with RAG (pull actual quotes and details from indexed content)
    # -------------------------------------------------------------------
    collection_id = state.get("chroma_collection_id", f"brand_{job_id}")
    if collection_id:
        try:
            rag_context = query_brand_knowledge(
                collection_id=collection_id,
                question=f"{brand_profile['brand_name']} brand identity products services",
                agent="brand_extractor",
                max_chunks=8,
            )
            # Enrich with quality utility
            brand_profile = enrich_brand_profile(
                brand_profile, raw_pages, source_url, colors
            )
            print(f"[brand_extractor] RAG enrichment complete")
        except Exception as e:
            print(f"[brand_extractor] RAG enrichment skipped: {e}")
            # Still run enrich_brand_profile with what we have
            try:
                brand_profile = enrich_brand_profile(
                    brand_profile, raw_pages, source_url, colors
                )
            except Exception:
                pass

    # -------------------------------------------------------------------
    # Step 6: Attach colors to profile (both formats for compatibility)
    # -------------------------------------------------------------------
    brand_profile["colors"] = colors
    brand_profile["brand_colors"] = colors

    # -------------------------------------------------------------------
    # Step 7: Emit SSE event with full brand profile for frontend card
    # -------------------------------------------------------------------
    event = {
        "type": "brand_extractor",
        "stage": "brand_extractor",
        "status": "done",
        "message": (
            f"Brand identified: {brand_profile.get('brand_name', 'Unknown')} | "
            f"{brand_profile.get('brand_category', '')} | "
            f"tone: {brand_profile.get('brand_tone', '')}"
        ),
        "data": {
            # Send only what the frontend brand card needs — not the full dump
            "brand_name":           brand_profile.get("brand_name", ""),
            "brand_category":       brand_profile.get("brand_category", ""),
            "brand_tone":           brand_profile.get("brand_tone", ""),
            "target_audience":      brand_profile.get("target_audience", ""),
            "brand_promise":        brand_profile.get("brand_promise", ""),
            "usps":                 brand_profile.get("usps", []),
            "key_products_services":brand_profile.get("key_products_services", []),
            "competitive_edge":     brand_profile.get("competitive_edge", ""),
            "emotional_benefit":    brand_profile.get("emotional_benefit", ""),
            "brand_archetype":      brand_profile.get("brand_archetype", ""),
            "visual_style":         brand_profile.get("visual_style", ""),
            "pricing_model":        brand_profile.get("pricing_model", ""),
            "content_themes":       brand_profile.get("content_themes", []),
            "brand_voice_examples": brand_profile.get("brand_voice_examples", []),
            "colors":               colors,
        },
    }

    job_manager.emit(job_id, event)

    # -------------------------------------------------------------------
    # Step 8: Return ALL fields to state — every downstream agent reads these
    # -------------------------------------------------------------------
    return {
        # Core identity — used by all agents
        "brand_profile":         brand_profile,
        "brand_colors":          brand_colors,
        "brand_name":            brand_profile.get("brand_name", ""),
        "brand_tone":            brand_profile.get("brand_tone", "professional"),
        "brand_category":        brand_profile.get("brand_category", "Business"),
        "target_audience":       brand_profile.get("target_audience", ""),
        "usps":                  brand_profile.get("usps", []),

        # Extended brand intelligence — used by copywriter, email, ad agents
        "brand_promise":         brand_profile.get("brand_promise", ""),
        "key_products_services": brand_profile.get("key_products_services", []),
        "competitive_edge":      brand_profile.get("competitive_edge", ""),
        "brand_voice_examples":  brand_profile.get("brand_voice_examples", []),
        "emotional_benefit":     brand_profile.get("emotional_benefit", ""),
        "brand_archetype":       brand_profile.get("brand_archetype", "Sage"),
        "content_themes":        brand_profile.get("content_themes", []),
        "industry_language":     brand_profile.get("industry_language", []),

        # Layout decisions — used by layout_agent and asset_generator
        "visual_style":          brand_profile.get("visual_style", "minimal"),
        "pricing_model":         brand_profile.get("pricing_model", "unknown"),

        "events": [event],
    }