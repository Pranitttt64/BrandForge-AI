import json
import re
from difflib import SequenceMatcher
from urllib.parse import urlparse


GENERIC_PHRASES = (
    "your brand",
    "your business",
    "our solution",
    "lorem ipsum",
    "unlock your potential",
    "transform your business",
    "revolutionize",
    "elevate your",
)


def compact_text(text: str, limit: int = 240) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    return cleaned[:limit].rstrip()


def parse_json_lenient(raw: str):
    """Parse malformed-but-close LLM JSON without throwing."""
    if not raw:
        return {}
    cleaned = re.sub(r"```(?:json)?", "", str(raw), flags=re.I).strip().rstrip("`")
    start_candidates = [idx for idx in [cleaned.find("{"), cleaned.find("[")] if idx != -1]
    if not start_candidates:
        return {}
    start = min(start_candidates)
    end = max(cleaned.rfind("}"), cleaned.rfind("]")) + 1
    if end <= start:
        return {}
    candidate = cleaned[start:end]
    candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
    try:
        return json.loads(candidate)
    except Exception:
        return {}


def is_generic(value: str) -> bool:
    lower = str(value or "").lower()
    return not lower.strip() or any(phrase in lower for phrase in GENERIC_PHRASES)


def unique_list(items, limit: int = 8) -> list[str]:
    selected: list[str] = []
    for item in items or []:
        text = compact_text(item, 260)
        if len(text) < 3 or is_generic(text):
            continue
        if any(SequenceMatcher(None, text.lower(), prev.lower()).ratio() > 0.82 for prev in selected):
            continue
        selected.append(text)
        if len(selected) >= limit:
            break
    return selected


def infer_brand_name(url: str, raw_pages: dict) -> str:
    for page_text in (raw_pages or {}).values():
        for pattern in [r"Title:\s*([^\n|]+)", r"H1:\s*([^\n|]+)", r"\[PAGE:\s*https?://(?:www\.)?([^/\]]+)"]:
            match = re.search(pattern, page_text or "", flags=re.I)
            if match:
                name = compact_text(match.group(1), 80)
                name = re.sub(r"\s*[-|•].*$", "", name).strip()
                if name and len(name) > 2:
                    return name
    host = urlparse(url or "").netloc.replace("www.", "")
    return host.split(".")[0].replace("-", " ").title() if host else "Brand"


def extract_candidate_phrases(raw_pages: dict, limit: int = 12) -> list[str]:
    joined = "\n".join((raw_pages or {}).values())
    candidates: list[str] = []
    for marker in ["Headings:", "Brand sections:", "Paragraphs:", "Footer:"]:
        for part in joined.split(marker)[1:]:
            lines = [compact_text(line, 180) for line in part.splitlines()]
            candidates.extend([line for line in lines if 18 <= len(line) <= 180])
    if len(candidates) < 5:
        sentences = re.split(r"(?<=[.!?])\s+", compact_text(joined, 8000))
        candidates.extend([s for s in sentences if 35 <= len(s) <= 180])
    return unique_list(candidates, limit=limit)


def enrich_brand_profile(profile: dict, raw_pages: dict, url: str, colors: dict | None = None) -> dict:
    profile = dict(profile or {})
    candidates = extract_candidate_phrases(raw_pages)
    brand_name = profile.get("brand_name")
    if is_generic(brand_name):
        brand_name = infer_brand_name(url, raw_pages)

    usps = unique_list(profile.get("usps"), limit=5)
    while len(usps) < 3 and candidates:
        usps.append(candidates.pop(0))
        usps = unique_list(usps, limit=5)

    products = unique_list(profile.get("key_products_services") or profile.get("product_categories"), limit=5)
    while len(products) < 3 and candidates:
        products.append(candidates.pop(0))
        products = unique_list(products, limit=5)

    target = compact_text(profile.get("target_audience"), 220)
    if is_generic(target):
        target = f"Customers evaluating {brand_name} for {products[0] if products else 'its core offer'}"

    category = compact_text(profile.get("brand_category"), 120)
    if is_generic(category):
        category = "Brand-led business"

    promise = compact_text(profile.get("brand_promise"), 260)
    if is_generic(promise):
        promise = f"{brand_name} helps {target} get {usps[0].lower() if usps else 'a clearer, more useful experience'}."

    edge = compact_text(profile.get("competitive_edge"), 260)
    if is_generic(edge):
        edge = usps[1] if len(usps) > 1 else promise

    voice_examples = unique_list(profile.get("brand_voice_examples"), limit=3)
    while len(voice_examples) < 2 and candidates:
        voice_examples.append(candidates.pop(0))
        voice_examples = unique_list(voice_examples, limit=3)

    profile.update({
        "brand_name": brand_name,
        "brand_category": category,
        "brand_tone": profile.get("brand_tone") or "professional",
        "target_audience": target,
        "usps": usps[:5],
        "brand_promise": promise,
        "key_products_services": products[:5],
        "competitive_edge": edge,
        "brand_voice_examples": voice_examples[:3],
        "brand_colors": colors or profile.get("brand_colors") or profile.get("colors") or {},
    })
    return profile


def normalize_copy_output(copy_output: dict, state: dict) -> dict:
    brand = state.get("brand_name") or state.get("brand_profile", {}).get("brand_name") or "Brand"
    usps = state.get("usps") or state.get("brand_profile", {}).get("usps") or []
    promise = state.get("brand_promise") or state.get("brand_profile", {}).get("brand_promise") or ""

    out = dict(copy_output or {})
    out.setdefault("headlines", {})
    out.setdefault("value_props", {})
    out.setdefault("call_to_actions", {})
    for tone in ["bold", "friendly", "professional"]:
        out["headlines"][tone] = unique_list(out["headlines"].get(tone), 3)
        while len(out["headlines"][tone]) < 3:
            seed = usps[len(out["headlines"][tone]) % len(usps)] if usps else promise
            out["headlines"][tone].append(compact_text(f"{brand}: {seed}", 72))

        out["value_props"][tone] = unique_list(out["value_props"].get(tone), 3)
        while len(out["value_props"][tone]) < 3:
            seed = usps[len(out["value_props"][tone]) % len(usps)] if usps else promise
            out["value_props"][tone].append(seed)

        out["call_to_actions"][tone] = unique_list(out["call_to_actions"].get(tone), 3)
        while len(out["call_to_actions"][tone]) < 3:
            out["call_to_actions"][tone].append([f"Explore {brand}", "Request a Demo", "Get Started"][len(out["call_to_actions"][tone])])

    if is_generic(out.get("tagline")):
        out["tagline"] = promise or f"{brand}, built around what customers need."
    if is_generic(out.get("elevator_pitch")):
        out["elevator_pitch"] = f"{brand} serves {state.get('target_audience', 'customers')} with {', '.join(usps[:3])}. {promise}"
    return out


def normalize_email_output(email_output: dict, state: dict) -> dict:
    brand = state.get("brand_name") or state.get("brand_profile", {}).get("brand_name") or "Brand"
    usps = state.get("usps") or []
    services = state.get("key_products_services") or []
    emails = email_output.get("emails") if isinstance(email_output, dict) else None
    if not isinstance(emails, list):
        emails = []
    by_type = {item.get("type"): dict(item) for item in emails if isinstance(item, dict)}
    normalized = []
    for email_type, headline in [("welcome", f"Welcome to {brand}"), ("promo", f"See what {brand} can do"), ("reengagement", f"Come back to {brand}")]:
        item = by_type.get(email_type, {})
        body = compact_text(item.get("body"), 900)
        if len(body.split()) < 45:
            body = (
                f"{brand} is built for {state.get('target_audience', 'customers')} with "
                f"{', '.join(usps[:3]) if usps else state.get('brand_promise', 'clear customer value')}. "
                f"Explore {', '.join(services[:3]) if services else 'the core offer'} and see how the brand can support your next decision. "
                f"This message gives readers a specific reason to act, using the real benefits found in the brand profile."
            )
        normalized.append({
            "type": email_type,
            "subject": item.get("subject") or headline,
            "headline": item.get("headline") or headline,
            "body": body,
            "cta_text": item.get("cta_text") or item.get("cta") or f"Explore {brand}",
        })
    return {"emails": normalized}


def normalize_ad_output(ad_output: dict, state: dict) -> dict:
    brand = state.get("brand_name") or "Brand"
    usps = state.get("usps") or []
    out = dict(ad_output or {})
    out["headlines"] = unique_list(out.get("headlines"), 5)
    while len(out["headlines"]) < 5:
        seed = usps[len(out["headlines"]) % len(usps)] if usps else state.get("brand_promise", "Better outcomes")
        out["headlines"].append(compact_text(f"{brand} {seed}", 40))
    out["body_copies"] = unique_list(out.get("body_copies"), 3)
    while len(out["body_copies"]) < 3:
        out["body_copies"].append(f"{brand} helps {state.get('target_audience', 'customers')} with {usps[0] if usps else state.get('brand_promise', 'specific value')}. Explore the offer and take the next step.")
    out["ctas"] = unique_list(out.get("ctas"), 3) or [f"Explore {brand}", "Start Today", "Request Details"]
    out["google_rsa"] = out.get("google_rsa") or {}
    out["google_rsa"]["headlines"] = [compact_text(h, 30) for h in unique_list(out["google_rsa"].get("headlines"), 3)]
    out["google_rsa"]["descriptions"] = [compact_text(d, 90) for d in unique_list(out["google_rsa"].get("descriptions"), 2)]
    while len(out["google_rsa"]["headlines"]) < 3:
        out["google_rsa"]["headlines"].append(compact_text(out["headlines"][len(out["google_rsa"]["headlines"])], 30))
    while len(out["google_rsa"]["descriptions"]) < 2:
        out["google_rsa"]["descriptions"].append(compact_text(out["body_copies"][len(out["google_rsa"]["descriptions"])], 90))
    if is_generic(out.get("meta_primary_text")):
        out["meta_primary_text"] = out["body_copies"][0]
    return out
