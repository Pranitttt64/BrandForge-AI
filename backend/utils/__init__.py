"""
Utils package — BrandForge AI
parse_llm_json is the single most-called utility in the pipeline.
Every agent depends on it. It must be bulletproof.
"""

from __future__ import annotations

import json
import re


def parse_llm_json(raw: str) -> dict:
    """
    Robustly extract and parse JSON from LLM output.

    Handles all common LLM output failure modes:
    - Markdown code fences (```json ... ```)
    - Leading/trailing explanation text
    - Trailing commas before } or ]
    - Escaped single-quotes instead of double-quotes
    - Unicode escape sequences
    - Partial JSON with recoverable structure
    """
    if not raw:
        return {}

    text = str(raw).strip()

    # --- Pass 1: strip markdown fences ---
    text = re.sub(r"```(?:json|python|text)?\s*", "", text)
    text = re.sub(r"```\s*$", "", text)
    text = text.strip().strip("`").strip()

    # --- Pass 2: try direct parse ---
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
        if isinstance(result, list) and result and isinstance(result[0], dict):
            return result[0]
    except Exception:
        pass

    # --- Pass 3: find outermost { } block ---
    brace_start = text.find("{")
    brace_end   = text.rfind("}") + 1
    if brace_start != -1 and brace_end > brace_start:
        chunk = text[brace_start:brace_end]
        try:
            result = json.loads(chunk)
            if isinstance(result, dict):
                return result
        except Exception:
            pass

        # --- Pass 4: repair common issues then retry ---
        repaired = chunk
        # Remove trailing commas before } or ]
        repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
        # Replace Python True/False/None literals
        repaired = repaired.replace("True", "true").replace("False", "false").replace("None", "null")
        # Strip control characters
        repaired = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", repaired)
        try:
            result = json.loads(repaired)
            if isinstance(result, dict):
                return result
        except Exception:
            pass

        # --- Pass 5: try json5-style single-quote replacement (crude but recovers some) ---
        try:
            single_to_double = re.sub(r"'([^']*)'", lambda m: '"' + m.group(1) + '"', repaired)
            result = json.loads(single_to_double)
            if isinstance(result, dict):
                return result
        except Exception:
            pass

    print(f"[parse_llm_json] All parse attempts failed — raw length: {len(raw)}")
    return {}