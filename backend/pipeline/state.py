"""
LangGraph state schema for BrandForge AI pipeline.
All fields are Optional with defaults so nodes never get KeyError.
"""

import operator
from typing import Annotated, TypedDict, Optional


class BrandForgeState(TypedDict, total=False):
    # ── Input ────────────────────────────────────────────────────
    url:                    str
    job_id:                 str

    # ── Stage 1: Scraping ────────────────────────────────────────
    raw_pages:              dict        # {url: text_content}
    scrape_status:          str         # "success"|"partial"|"failed"

    # ── Stage 2: Brand Extraction ────────────────────────────────
    brand_profile:          dict        # full extracted brand dict
    brand_name:             str
    brand_tone:             str         # "professional"|"bold"|"playful" etc
    brand_category:         str         # "SaaS"|"Fintech"|"Retail" etc
    target_audience:        str
    brand_promise:          str
    competitive_edge:       str
    usps:                   list        # list of USP strings
    key_products_services:  list
    brand_colors:           dict        # {primary, secondary, accent, background, text}

    # ── Stage 3: RAG ─────────────────────────────────────────────
    chroma_collection_id:   str

    # ── Stage 4: Creative Agents (parallel) ──────────────────────
    copy_output:            dict        # headlines, taglines, CTAs, etc
    layout_output:          dict        # template, typography_mood, etc
    email_output:           dict        # email_welcome, email_promo, email_reengagement
    ad_output:              dict        # google_rsa, instagram, linkedin, hooks

    # ── Stage 5: Critic ──────────────────────────────────────────
    critic_feedback:        dict
    critic_approved:        bool

    # ── Stage 6: Asset Generation ────────────────────────────────
    flyer_pdf_path:         str
    social_card_path:       str
    email_html_path:        str
    email_html_paths:       list
    ad_copy_pdf_path:       str

    # ── Stage 7: Packaging ───────────────────────────────────────
    zip_path:               str

    # ── Internal ─────────────────────────────────────────────────
    # Annotated with operator.add so parallel nodes can append concurrently
    events:                 Annotated[list, operator.add]


def make_initial_state(url: str, job_id: str) -> BrandForgeState:
    """
    Create a fully initialised state dict.
    Every field has a safe default so LangGraph never gets KeyError.
    """
    return BrandForgeState(
        url=url,
        job_id=job_id,
        raw_pages={},
        scrape_status="",
        brand_profile={},
        brand_name="",
        brand_tone="",
        brand_category="",
        target_audience="",
        brand_promise="",
        competitive_edge="",
        usps=[],
        key_products_services=[],
        brand_colors={},
        chroma_collection_id="",
        copy_output={},
        layout_output={},
        email_output={},
        ad_output={},
        critic_feedback={},
        critic_approved=False,
        flyer_pdf_path="",
        social_card_path="",
        email_html_path="",
        email_html_paths=[],
        ad_copy_pdf_path="",
        zip_path="",
        events=[],
    )