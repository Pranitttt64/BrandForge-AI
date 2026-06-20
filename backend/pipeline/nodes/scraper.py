import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from job_manager import job_manager
from pipeline.state import BrandForgeState


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SECTION_HINTS = (
    "about", "mission", "values", "feature", "service", "product",
    "pricing", "price", "plan", "team", "story", "benefit", "why",
    "how", "what", "solution", "platform", "offer", "testimonial",
    "review", "customer", "case", "result", "trust", "partner",
    "integration", "faq", "help", "support", "hero", "banner",
    "highlight", "stat", "number", "metric", "advantage", "unique",
)

LINK_PRIORITIES = (
    "about", "product", "products", "service", "services", "features",
    "pricing", "customers", "case", "story", "mission", "team", "why",
    "how", "platform", "solution", "overview",
)

# Max characters to keep per page (prevent token explosion downstream)
MAX_CHARS_PER_PAGE = 8000
# Max total chars across all pages
MAX_TOTAL_CHARS = 40000
# Concurrency limit for Jina requests
JINA_CONCURRENCY = 6


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

def _same_domain(base_url: str, candidate: str) -> bool:
    base = urlparse(base_url)
    parsed = urlparse(candidate)
    if parsed.scheme not in ("http", "https"):
        return False
    base_host = base.netloc.removeprefix("www.")
    cand_host = parsed.netloc.removeprefix("www.")
    return base_host == cand_host


def _clean_url(url: str) -> str:
    url = url.split("#")[0].split("?")[0].rstrip("/")
    return url


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _is_junk_url(url: str) -> bool:
    """Filter out URLs that won't have useful brand content."""
    junk_patterns = (
        "/cdn-", "/static/", "/assets/", "/images/", "/img/",
        ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".pdf",
        ".mp4", ".mp3", ".zip", ".css", ".js", ".xml",
        "/login", "/signup", "/register", "/auth",
        "/privacy", "/terms", "/cookie", "/legal",
        "/sitemap", "/robots",
        "/blog/", "/news/", "/press/", "/events/",
        "/careers/", "/jobs/",
        "javascript:", "mailto:", "tel:",
    )
    lower = url.lower()
    return any(p in lower for p in junk_patterns)


def _prioritize_links(links: list[str], limit: int) -> list[str]:
    def score(link: str) -> tuple[int, int]:
        lower = link.lower()
        priority = min(
            (i for i, hint in enumerate(LINK_PRIORITIES) if hint in lower),
            default=99,
        )
        depth = urlparse(link).path.count("/")
        return (priority, depth)

    unique = list(dict.fromkeys(lnk for lnk in links if not _is_junk_url(lnk)))
    return sorted(unique, key=score)[:limit]


def _extract_links_from_html(html: str, current_url: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html or "", "html.parser")
    links: list[str] = []
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if not href:
            continue
        full = _clean_url(urljoin(current_url, href))
        if _same_domain(base_url, full) and full not in links and full != base_url:
            links.append(full)
    return links


def _extract_links_from_text(text: str, current_url: str, base_url: str) -> list[str]:
    """Extract links from Jina markdown-style output."""
    links: list[str] = []
    patterns = [
        r"\[[^\]]+\]\((https?://[^)\s]+)\)",
        r"\[[^\]]+\]\((/[^)\s]+)\)",
    ]
    for pattern in patterns:
        for href in re.findall(pattern, text or ""):
            full = _clean_url(urljoin(current_url, href))
            if _same_domain(base_url, full) and full not in links:
                links.append(full)
    return links


# ---------------------------------------------------------------------------
# Content extraction — the heart of the scraper
# ---------------------------------------------------------------------------

def _extract_json_ld(soup: BeautifulSoup) -> str:
    """Extract schema.org JSON-LD structured data — goldmine for brand info."""
    results: list[str] = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, list):
                data = data[0] if data else {}
            useful_keys = (
                "name", "description", "slogan", "brand", "offers",
                "aggregateRating", "review", "numberOfEmployees",
                "foundingDate", "award", "knowsAbout", "hasOfferCatalog",
                "serviceType", "category", "keywords",
            )
            extracted = {k: v for k, v in data.items() if k in useful_keys and v}
            if extracted:
                results.append("Structured data: " + json.dumps(extracted, ensure_ascii=False))
        except Exception:
            pass
    return "\n".join(results)


def _extract_og_tags(soup: BeautifulSoup) -> str:
    """Extract Open Graph and Twitter card meta tags."""
    parts: list[str] = []
    og_keys = (
        "og:title", "og:description", "og:site_name", "og:type",
        "twitter:title", "twitter:description", "twitter:site",
    )
    for key in og_keys:
        tag = soup.find("meta", property=key) or soup.find("meta", attrs={"name": key})
        if tag and tag.get("content"):
            label = key.split(":")[-1].replace("-", "_")
            parts.append(f"OG {label}: " + _normalize_space(tag["content"]))
    return "\n".join(parts)


def _extract_lists(soup: BeautifulSoup) -> str:
    """Extract list items — features, benefits, and USPs almost always live in <ul><li>."""
    results: list[str] = []
    for ul in soup.find_all(["ul", "ol"]):
        items = [
            _normalize_space(li.get_text(" ", strip=True))
            for li in ul.find_all("li")
        ]
        items = [it for it in items if len(it) > 10 and len(it) < 300]
        if 2 <= len(items) <= 20:
            results.append("• " + "\n• ".join(items))
    return "\n\n".join(results[:15]) if results else ""


def _extract_cta_buttons(soup: BeautifulSoup) -> str:
    """Extract button and CTA text — reveals brand action language."""
    ctas: list[str] = []
    selectors = ["button", "a"]
    cta_classes = ("cta", "btn", "button", "action", "primary", "hero", "signup", "start")
    for tag in soup.find_all(selectors):
        classes = " ".join(tag.get("class") or []).lower()
        text = _normalize_space(tag.get_text(" ", strip=True))
        if (
            text
            and 3 < len(text) < 80
            and any(c in classes for c in cta_classes)
            and text not in ctas
        ):
            ctas.append(text)
    return "CTAs/Buttons: " + " | ".join(ctas[:15]) if ctas else ""


def _extract_testimonials(soup: BeautifulSoup) -> str:
    """Extract social proof — reviews, quotes, testimonials."""
    results: list[str] = []
    testimonial_hints = (
        "testimonial", "review", "quote", "social-proof",
        "customer", "feedback", "trust",
    )
    for tag in soup.find_all(True):
        attrs = " ".join(
            str(v).lower()
            for key in ("class", "id", "data-testid")
            for v in ([tag.get(key)] if isinstance(tag.get(key), str) else (tag.get(key) or []))
        )
        if any(h in attrs for h in testimonial_hints):
            text = _normalize_space(tag.get_text(" ", strip=True))
            if 30 < len(text) < 500 and text not in results:
                results.append(text)
    # Also grab blockquotes
    for bq in soup.find_all("blockquote"):
        text = _normalize_space(bq.get_text(" ", strip=True))
        if 20 < len(text) < 500 and text not in results:
            results.append(text)
    return "Testimonials/Social proof:\n" + "\n---\n".join(results[:8]) if results else ""


def _extract_stats_numbers(soup: BeautifulSoup) -> str:
    """Extract stat blocks — '10M users', '99.9% uptime', '$2B processed'."""
    stat_hints = ("stat", "metric", "number", "count", "figure", "highlight", "kpi")
    results: list[str] = []
    for tag in soup.find_all(True):
        attrs = " ".join(
            str(v).lower()
            for key in ("class", "id")
            for v in ([tag.get(key)] if isinstance(tag.get(key), str) else (tag.get(key) or []))
        )
        if any(h in attrs for h in stat_hints):
            text = _normalize_space(tag.get_text(" ", strip=True))
            if 3 < len(text) < 200 and text not in results:
                results.append(text)
    # Also look for patterns like "10M+", "$2B", "99.9%"
    all_text = soup.get_text(" ", strip=True)
    stat_pattern = re.findall(
        r"\b(\d[\d,\.]*[MKBmkb%+xX]*\+?\s{0,3}[A-Za-z]{0,20})\b",
        all_text,
    )
    notable = [s.strip() for s in stat_pattern if len(s.strip()) > 2][:20]
    if notable:
        results.append("Key numbers: " + " | ".join(dict.fromkeys(notable)))
    return "Stats & metrics:\n" + "\n".join(results[:10]) if results else ""


def _extract_pricing(soup: BeautifulSoup) -> str:
    """Extract pricing information — plans, tiers, prices."""
    pricing_hints = ("pricing", "price", "plan", "tier", "cost", "billing", "subscription")
    results: list[str] = []
    for tag in soup.find_all(True):
        attrs = " ".join(
            str(v).lower()
            for key in ("class", "id")
            for v in ([tag.get(key)] if isinstance(tag.get(key), str) else (tag.get(key) or []))
        )
        if any(h in attrs for h in pricing_hints):
            text = _normalize_space(tag.get_text(" ", strip=True))
            if 10 < len(text) < 600 and text not in results:
                results.append(text)
    return "Pricing/Plans:\n" + "\n".join(results[:6]) if results else ""


def _extract_brand_sections(soup: BeautifulSoup) -> str:
    """Extract content from semantically-hinted brand sections."""
    seen: set[str] = set()
    blocks: list[str] = []
    for tag in soup.find_all(True):
        attrs = " ".join(
            str(v).lower()
            for key in ("class", "id", "aria-label", "data-section", "data-block")
            for v in ([tag.get(key)] if isinstance(tag.get(key), str) else (tag.get(key) or []))
        )
        if any(hint in attrs for hint in SECTION_HINTS):
            text = _normalize_space(tag.get_text(" ", strip=True))
            key = text[:80].lower()
            if len(text) > 40 and key not in seen:
                seen.add(key)
                blocks.append(text)
    return "Brand sections:\n" + "\n\n".join(blocks[:20]) if blocks else ""


def extract_structured_text(content: str, page_url: str, is_html: bool = True) -> str:
    """
    Master extraction function. Pulls every meaningful signal from a page.
    Returns a rich, labeled text block ready for RAG chunking.
    """
    if not content or len(content.strip()) < 50:
        return ""

    parts: list[str] = [f"[SOURCE PAGE: {page_url}]"]

    if not is_html:
        # Jina returns markdown-ish text, not raw HTML
        clean = _normalize_space(content)
        parts.append("Content:\n" + clean[:MAX_CHARS_PER_PAGE])
        return "\n\n".join(parts)

    soup = BeautifulSoup(content, "html.parser")

    # Remove noise elements first
    for el in soup(["script", "style", "noscript", "svg", "path", "iframe",
                    "nav > *", "head"]):
        el.decompose()

    # --- Core identity signals ---
    title = _normalize_space(soup.title.get_text(" ", strip=True)) if soup.title else ""
    if title:
        parts.append(f"Page title: {title}")

    og = _extract_og_tags(soup)
    if og:
        parts.append(og)

    meta_desc = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    if meta_desc and meta_desc.get("content"):
        parts.append("Meta description: " + _normalize_space(meta_desc["content"]))

    meta_kw = soup.find("meta", attrs={"name": re.compile("^keywords$", re.I)})
    if meta_kw and meta_kw.get("content"):
        parts.append("Meta keywords: " + _normalize_space(meta_kw["content"]))

    # --- JSON-LD structured data ---
    jsonld = _extract_json_ld(soup)
    if jsonld:
        parts.append(jsonld)

    # --- Headings hierarchy ---
    h1s = list(dict.fromkeys(
        _normalize_space(h.get_text(" ", strip=True))
        for h in soup.find_all("h1")
        if _normalize_space(h.get_text(" ", strip=True))
    ))
    if h1s:
        parts.append("H1 headlines: " + " | ".join(h1s[:5]))

    h2s = list(dict.fromkeys(
        _normalize_space(h.get_text(" ", strip=True))
        for h in soup.find_all("h2")
        if _normalize_space(h.get_text(" ", strip=True))
    ))
    if h2s:
        parts.append("H2 subheadings:\n" + "\n".join(h2s[:12]))

    h3s = list(dict.fromkeys(
        _normalize_space(h.get_text(" ", strip=True))
        for h in soup.find_all("h3")
        if _normalize_space(h.get_text(" ", strip=True))
    ))
    if h3s:
        parts.append("H3 sections:\n" + "\n".join(h3s[:12]))

    # --- Paragraphs ---
    paras = [
        _normalize_space(p.get_text(" ", strip=True))
        for p in soup.find_all("p")
    ]
    paras = [p for p in paras if 25 < len(p) < 800]
    paras = list(dict.fromkeys(paras))
    if paras:
        parts.append("Body text:\n" + "\n\n".join(paras[:25]))

    # --- Feature/benefit lists ---
    lists_text = _extract_lists(soup)
    if lists_text:
        parts.append("Feature/benefit lists:\n" + lists_text)

    # --- CTAs ---
    cta_text = _extract_cta_buttons(soup)
    if cta_text:
        parts.append(cta_text)

    # --- Brand sections by class/id hints ---
    brand_sections = _extract_brand_sections(soup)
    if brand_sections:
        parts.append(brand_sections)

    # --- Testimonials & social proof ---
    testimonials = _extract_testimonials(soup)
    if testimonials:
        parts.append(testimonials)

    # --- Stats & metrics ---
    stats = _extract_stats_numbers(soup)
    if stats:
        parts.append(stats)

    # --- Pricing ---
    pricing = _extract_pricing(soup)
    if pricing:
        parts.append(pricing)

    # --- Footer (taglines often live here) ---
    footer = soup.find("footer")
    if footer:
        footer_text = _normalize_space(footer.get_text(" ", strip=True))
        if footer_text and len(footer_text) > 20:
            parts.append("Footer content: " + footer_text[:600])

    full = "\n\n".join(parts)
    return full[:MAX_CHARS_PER_PAGE]


# ---------------------------------------------------------------------------
# Sitemap discovery
# ---------------------------------------------------------------------------

async def _fetch_sitemap_urls(base_url: str, client: httpx.AsyncClient) -> list[str]:
    """Try to grab internal URLs from sitemap.xml — instant multi-page discovery."""
    urls: list[str] = []
    parsed = urlparse(base_url)
    sitemap_candidates = [
        f"{parsed.scheme}://{parsed.netloc}/sitemap.xml",
        f"{parsed.scheme}://{parsed.netloc}/sitemap_index.xml",
        f"{parsed.scheme}://{parsed.netloc}/robots.txt",
    ]
    for sitemap_url in sitemap_candidates:
        try:
            resp = await client.get(sitemap_url, timeout=10.0)
            if resp.status_code != 200:
                continue
            text = resp.text
            if "sitemap" in sitemap_url and "<loc>" in text:
                found = re.findall(r"<loc>\s*(https?://[^<]+)\s*</loc>", text)
                for u in found:
                    u = _clean_url(u)
                    if _same_domain(base_url, u) and not _is_junk_url(u) and u not in urls:
                        urls.append(u)
            elif "robots.txt" in sitemap_url:
                sm_refs = re.findall(r"Sitemap:\s*(https?://[^\s]+)", text, re.IGNORECASE)
                for sm in sm_refs:
                    try:
                        sm_resp = await client.get(sm.strip(), timeout=10.0)
                        if sm_resp.status_code == 200 and "<loc>" in sm_resp.text:
                            found = re.findall(r"<loc>\s*(https?://[^<]+)\s*</loc>", sm_resp.text)
                            for u in found:
                                u = _clean_url(u)
                                if _same_domain(base_url, u) and not _is_junk_url(u) and u not in urls:
                                    urls.append(u)
                    except Exception:
                        pass
            if urls:
                break
        except Exception:
            pass
    return urls[:30]


# ---------------------------------------------------------------------------
# Jina Reader fetching (concurrent)
# ---------------------------------------------------------------------------

async def _fetch_jina_single(
    url: str,
    base_url: str,
    client: httpx.AsyncClient,
) -> dict[str, Any] | None:
    """Fetch one URL via Jina Reader."""
    try:
        resp = await client.get(
            f"https://r.jina.ai/{url}",
            headers={"Accept": "text/plain"},
            timeout=40.0,
        )
        if resp.status_code >= 400:
            return None
        text = resp.text or ""
        if len(text.strip()) < 200:
            return None

        # Jina returns markdown/text — parse it for structure
        # Also try to get HTML version for richer extraction
        html_resp = None
        try:
            html_resp = await client.get(url, timeout=20.0, follow_redirects=True)
        except Exception:
            pass

        if html_resp and html_resp.status_code == 200:
            structured = extract_structured_text(html_resp.text, url, is_html=True)
            # Merge: use structured HTML extraction PLUS Jina text
            combined = structured + "\n\nJina reader text:\n" + text[:3000]
        else:
            structured = extract_structured_text(text, url, is_html=False)
            combined = structured

        links = _extract_links_from_text(text, url, base_url)
        if html_resp and html_resp.status_code == 200:
            links += _extract_links_from_html(html_resp.text, url, base_url)
        links = list(dict.fromkeys(links))

        return {
            "url": url,
            "text": combined[:MAX_CHARS_PER_PAGE],
            "links": links,
            "char_count": len(combined),
        }
    except Exception as e:
        print(f"[scraper] Jina failed {url}: {e}")
        return None


async def _fetch_jina_concurrent(
    urls: list[str],
    base_url: str,
    client: httpx.AsyncClient,
    emit_fn=None,
    start_count: int = 0,
) -> dict[str, str]:
    """Fetch multiple URLs concurrently via Jina with a semaphore."""
    sem = asyncio.Semaphore(JINA_CONCURRENCY)
    results: dict[str, str] = {}

    async def _guarded(url: str, idx: int):
        async with sem:
            result = await _fetch_jina_single(url, base_url, client)
            if result and result["char_count"] > 200:
                results[url] = result["text"]
                if emit_fn:
                    emit_fn({
                        "type": "scraper",
                        "stage": "scraper",
                        "status": "progress",
                        "message": f"Scraped page {start_count + idx + 1}: {url}",
                    })
                return result["links"]
            return []

    tasks = [_guarded(url, i) for i, url in enumerate(urls)]
    all_link_lists = await asyncio.gather(*tasks)

    # Return discovered links from all pages
    discovered: list[str] = []
    for links in all_link_lists:
        for lnk in (links or []):
            if lnk not in discovered:
                discovered.append(lnk)
    results["__discovered_links__"] = discovered  # type: ignore
    return results


# ---------------------------------------------------------------------------
# Playwright fallback (for JS-heavy SPAs)
# ---------------------------------------------------------------------------

async def _fetch_playwright_batch(
    urls: list[str],
    base_url: str,
    emit_fn=None,
    start_count: int = 0,
) -> dict[str, str]:
    """Playwright fetch for JS-rendered sites. Used as fallback."""
    local_browser_path = Path(__file__).resolve().parents[2] / "ms-playwright"
    if local_browser_path.exists():
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(local_browser_path))

    pages_data: dict[str, str] = {}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        try:
            for idx, url in enumerate(urls):
                page = await context.new_page()
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    # Wait a bit for dynamic content
                    try:
                        await page.wait_for_load_state("networkidle", timeout=8000)
                    except Exception:
                        pass

                    html = await page.content()
                    # Also grab inner text for any missed dynamic content
                    inner = await page.evaluate(
                        "() => document.body ? document.body.innerText : ''"
                    )

                    structured = extract_structured_text(html, url, is_html=True)
                    # Append any dynamic text not already captured
                    if inner and len(inner) > 200:
                        structured += "\n\nDynamic page text:\n" + _normalize_space(inner)[:3000]

                    # Extract links
                    hrefs = await page.evaluate(
                        "() => Array.from(document.querySelectorAll('a[href]'))"
                        ".map(a => a.href).filter(h => h.startsWith('http'))"
                    )
                    links = [
                        _clean_url(h) for h in hrefs
                        if _same_domain(base_url, h) and not _is_junk_url(h)
                    ]
                    pages_data[url] = structured[:MAX_CHARS_PER_PAGE]

                    if emit_fn:
                        emit_fn({
                            "type": "scraper",
                            "stage": "scraper",
                            "status": "progress",
                            "message": f"Scraped page {start_count + idx + 1} via browser: {url}",
                        })

                    # Store discovered links temporarily
                    if "__discovered_links__" not in pages_data:
                        pages_data["__discovered_links__"] = []  # type: ignore
                    pages_data["__discovered_links__"] += [  # type: ignore
                        lnk for lnk in links
                        if lnk not in pages_data["__discovered_links__"]  # type: ignore
                    ]

                except Exception as e:
                    print(f"[scraper] Playwright page error {url}: {e}")
                finally:
                    await page.close()
        finally:
            await context.close()
            await browser.close()

    return pages_data


# ---------------------------------------------------------------------------
# Content quality scoring
# ---------------------------------------------------------------------------

def _quality_score(text: str) -> float:
    """
    Score how information-rich a scraped page is (0.0 - 1.0).
    Used to decide whether to use Playwright fallback.
    """
    if not text or len(text) < 100:
        return 0.0
    score = min(len(text) / MAX_CHARS_PER_PAGE, 1.0) * 0.4
    keyword_hits = sum(1 for h in SECTION_HINTS if h in text.lower())
    score += min(keyword_hits / 8, 1.0) * 0.3
    has_headings = "H1" in text or "H2" in text or "Headings:" in text
    score += 0.15 if has_headings else 0
    has_paras = "Body text:" in text or "Paragraphs:" in text
    score += 0.15 if has_paras else 0
    return round(score, 3)


def _dedupe_lines(text: str) -> str:
    """Remove duplicate lines while preserving structure."""
    seen: set[str] = set()
    lines: list[str] = []
    for line in (text or "").splitlines():
        cleaned = _normalize_space(line)
        if not cleaned:
            lines.append("")
            continue
        key = cleaned.lower()
        if key in seen and len(cleaned) < 200:
            continue
        seen.add(key)
        lines.append(cleaned)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main scraper node
# ---------------------------------------------------------------------------

async def scraper_node_async(state: BrandForgeState) -> dict:
    job_id = state.get("job_id", "unknown")
    url = _clean_url(state["url"])
    base_url = url

    def emit(event: dict):
        job_manager.emit(job_id, event)

    emit({"type": "scraper", "stage": "scraper", "status": "running",
          "message": "Starting deep brand scrape..."})

    raw_pages: dict[str, str] = {}
    all_discovered_links: list[str] = []

    async with httpx.AsyncClient(
        timeout=40.0,
        follow_redirects=True,
        headers={"User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )},
    ) as client:

        # --- Step 1: Sitemap discovery (fast, free page inventory) ---
        emit({"type": "scraper", "stage": "scraper", "status": "progress",
              "message": "Checking sitemap for page inventory..."})
        sitemap_urls = await _fetch_sitemap_urls(base_url, client)

        # --- Step 2: Fetch homepage + priority pages concurrently via Jina ---
        # Build initial URL list: homepage + sitemap priority pages + known paths
        known_paths = [
            "/about", "/about-us", "/product", "/products", "/features",
            "/services", "/pricing", "/how-it-works", "/why-us",
            "/customers", "/solutions", "/platform",
        ]
        parsed_base = urlparse(base_url)
        known_urls = [
            _clean_url(f"{parsed_base.scheme}://{parsed_base.netloc}{p}")
            for p in known_paths
        ]

        # Merge: homepage first, then sitemap, then known paths
        candidate_urls = [base_url]
        for u in sitemap_urls + known_urls:
            if u not in candidate_urls and not _is_junk_url(u):
                candidate_urls.append(u)

        # Fetch first batch (homepage + top candidates) concurrently
        first_batch = _prioritize_links(candidate_urls[1:], 9)
        batch_urls = [base_url] + first_batch  # homepage always first

        emit({"type": "scraper", "stage": "scraper", "status": "progress",
              "message": f"Fetching {len(batch_urls)} pages concurrently..."})

        jina_results = await _fetch_jina_concurrent(
            batch_urls, base_url, client, emit_fn=emit, start_count=0
        )

        discovered_links = jina_results.pop("__discovered_links__", [])
        for page_url, text in jina_results.items():
            if text and len(text) > 200:
                raw_pages[page_url] = _dedupe_lines(text)
        all_discovered_links += discovered_links

        # --- Step 3: Assess quality and decide on Playwright fallback ---
        homepage_text = raw_pages.get(base_url, "")
        homepage_quality = _quality_score(homepage_text)
        total_chars = sum(len(t) for t in raw_pages.values())
        pages_with_good_content = sum(
            1 for t in raw_pages.values() if _quality_score(t) > 0.3
        )

        needs_playwright = (
            homepage_quality < 0.25
            or total_chars < 3000
            or pages_with_good_content == 0
        )

        if needs_playwright:
            emit({"type": "scraper", "stage": "scraper", "status": "progress",
                  "message": "JS-heavy site detected — switching to browser rendering..."})
            playwright_urls = [base_url] + _prioritize_links(
                all_discovered_links + known_urls, 4
            )
            playwright_urls = [u for u in playwright_urls if u not in raw_pages][:5]
            if base_url not in raw_pages:
                playwright_urls = [base_url] + playwright_urls

            pw_results = await _fetch_playwright_batch(
                playwright_urls[:5], base_url, emit_fn=emit,
                start_count=len(raw_pages),
            )
            pw_links = pw_results.pop("__discovered_links__", [])
            for page_url, text in pw_results.items():
                if text and len(text) > 200:
                    raw_pages[page_url] = _dedupe_lines(text)
            all_discovered_links += (pw_links or [])

        # --- Step 4: If we still have budget, fetch more discovered links ---
        total_chars = sum(len(t) for t in raw_pages.values())
        remaining_budget = MAX_TOTAL_CHARS - total_chars
        pages_fetched = len(raw_pages)

        if remaining_budget > 5000 and pages_fetched < 12:
            extra_candidates = _prioritize_links(
                [u for u in all_discovered_links if u not in raw_pages],
                limit=max(0, 12 - pages_fetched),
            )
            if extra_candidates:
                emit({"type": "scraper", "stage": "scraper", "status": "progress",
                      "message": f"Fetching {len(extra_candidates)} more pages..."})
                extra_results = await _fetch_jina_concurrent(
                    extra_candidates, base_url, client,
                    emit_fn=emit, start_count=pages_fetched,
                )
                extra_results.pop("__discovered_links__", None)
                for page_url, text in extra_results.items():
                    if text and len(text) > 200 and page_url not in raw_pages:
                        raw_pages[page_url] = _dedupe_lines(text)

    # --- Step 5: Final cleanup and cap total size ---
    # Sort pages by quality score, keep best ones
    scored = sorted(
        raw_pages.items(),
        key=lambda kv: _quality_score(kv[1]),
        reverse=True,
    )
    final_pages: dict[str, str] = {}
    running_chars = 0
    for page_url, text in scored:
        if running_chars >= MAX_TOTAL_CHARS:
            break
        trimmed = text[:MAX_CHARS_PER_PAGE]
        final_pages[page_url] = trimmed
        running_chars += len(trimmed)

    total_chars = sum(len(t) for t in final_pages.values())
    scrape_status = (
        "success" if total_chars > 5000
        else "partial" if total_chars > 1000
        else "failed"
    )

    summary = (
        f"Scraped {len(final_pages)} pages | "
        f"{total_chars:,} chars | "
        f"Quality: {scrape_status}"
    )
    emit({
        "type": "scraper",
        "stage": "scraper",
        "status": "done",
        "message": summary,
    })
    print(f"[scraper] {summary}")

    return {
        "raw_pages": final_pages,
        "scrape_status": scrape_status,
        "events": [{"type": "scraper", "stage": "scraper",
                    "status": "done", "message": summary}],
    }


def scraper_node(state: BrandForgeState) -> dict:
    """Sync wrapper — LangGraph calls this, which runs the async version."""
    try:
        loop = asyncio.get_running_loop()
        # Already inside an event loop (LangGraph async context)
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, scraper_node_async(state))
            return future.result()
    except RuntimeError:
        return asyncio.run(scraper_node_async(state))