"""
LLM digest generator.
Primary: Claude Haiku. Fallback: Gemini 1.5 Flash.
Model-agnostic via config.yaml provider setting.
"""
import json
import os
import random
import time
from collections import Counter
from typing import List, Dict, Any

from models.intel_item import IntelItem
from utils.config_loader import get_config, get_secret
from llm.prompts import SYSTEM_PROMPT, DIGEST_PROMPT, WEEKLY_PROMPT


_LAST_GEMINI_REQUEST_TS = 0.0


def generate_digest(items: List[IntelItem], digest_type: str = "daily") -> Dict[str, Any]:
    """
    Generate a structured digest from a list of IntelItems.
    digest_type: "daily" | "weekly"
    Returns parsed JSON dict.
    """
    cfg = get_config()["llm"]
    provider = os.getenv("LLM_PROVIDER", cfg.get("provider", "claude"))
    fallback_provider = cfg.get("fallback_provider")

    # Serialize intel items for the prompt
    intel_data = [item.to_dict() for item in items]
    intel_json = json.dumps(intel_data, indent=2, default=str)

    prompt_template = WEEKLY_PROMPT if digest_type == "weekly" else DIGEST_PROMPT
    user_message = prompt_template.format(intel_json=intel_json)

    provider_chain = [provider]
    if fallback_provider and fallback_provider != provider:
        provider_chain.append(fallback_provider)

    errors = []
    for idx, selected_provider in enumerate(provider_chain):
        try:
            if selected_provider == "claude":
                return _generate_claude(user_message, cfg)
            if selected_provider == "gemini":
                return _generate_gemini(user_message, cfg)
            raise ValueError(f"Unknown LLM provider: {selected_provider}")
        except Exception as exc:
            errors.append(f"{selected_provider}: {exc}")
            has_next = idx < len(provider_chain) - 1
            if has_next:
                print(
                    f"[llm] Provider '{selected_provider}' failed ({exc}). "
                    f"Trying fallback '{provider_chain[idx + 1]}'."
                )
                continue

            if cfg.get("allow_emergency_digest", True):
                print("[llm] All providers failed. Returning emergency non-LLM digest.")
                return _build_emergency_digest(items, errors)

            raise RuntimeError(
                "All configured LLM providers failed: " + " | ".join(errors)
            ) from exc


def _generate_claude(user_message: str, cfg: dict) -> Dict[str, Any]:
    import anthropic

    api_key = get_secret("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set in .env")

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=cfg.get("model", "claude-haiku-4-5-20251001"),
        max_tokens=cfg.get("max_tokens", 2048),
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = response.content[0].text.strip()
    return _parse_json(raw)

def _generate_gemini(user_message: str, cfg: dict) -> Dict[str, Any]:
    from google import genai
    from google.genai import types

    api_key = get_secret("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in .env")

    client = genai.Client(api_key=api_key)
    max_retries = int(cfg.get("max_retries", 2))
    initial_delay = float(cfg.get("retry_initial_delay_sec", 2.0))
    backoff = float(cfg.get("retry_backoff_multiplier", 2.0))
    jitter = float(cfg.get("retry_jitter_sec", 0.5))

    delay = initial_delay
    for attempt in range(max_retries + 1):
        _throttle_gemini_requests(cfg)
        try:
            response = client.models.generate_content(
                model=cfg.get("model", "gemini-2.0-flash"),
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=cfg.get("temperature", 0.3),
                    max_output_tokens=cfg.get("max_tokens", 2048),
                ),
            )
            return _parse_json(response.text.strip())
        except Exception as exc:
            if not _is_quota_or_rate_limit_error(exc) or attempt >= max_retries:
                raise

            sleep_for = delay + random.uniform(0, jitter)
            print(
                f"[llm] Gemini rate/quota limit hit (attempt {attempt + 1}/{max_retries + 1}). "
                f"Retrying in {sleep_for:.1f}s..."
            )
            time.sleep(sleep_for)
            delay *= backoff

    raise RuntimeError("Gemini request failed after retries")


def _is_quota_or_rate_limit_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(token in msg for token in ["429", "resource_exhausted", "quota", "rate limit"])


def _build_emergency_digest(items: List[IntelItem], errors: List[str]) -> Dict[str, Any]:
    """Build a lightweight digest from collected data when LLM providers are unavailable."""
    by_domain = {
        "financial": [],
        "geopolitical": [],
        "cyber": [],
        "social": [],
    }
    sev_counter = Counter()

    for item in items:
        domain = item.domain.value
        if domain in by_domain:
            by_domain[domain].append(item)
        sev_counter[item.severity.value] += 1

    def top_lines(domain_items: List[IntelItem], max_items: int = 5) -> List[str]:
        lines = []
        for intel in domain_items[:max_items]:
            lines.append(f"{intel.title} ({intel.source})")
        return lines

    highest = "INFO"
    for level in ["critical", "high", "medium", "low", "info"]:
        if sev_counter[level] > 0:
            highest = level.upper()
            break

    return {
        "executive_brief": (
            f"Emergency digest generated without an LLM. {len(items)} total signals were collected "
            "and summarized directly from source headlines."
        ),
        "market_pulse": {
            "summary": f"{len(by_domain['financial'])} market signals captured.",
            "top_movers": top_lines(by_domain["financial"]),
            "severity": highest,
        },
        "geopolitical_watch": {
            "summary": f"{len(by_domain['geopolitical'])} geopolitical signals captured.",
            "key_events": top_lines(by_domain["geopolitical"]),
            "severity": highest,
        },
        "cyber_threat_board": {
            "summary": f"{len(by_domain['cyber'])} cyber signals captured.",
            "top_threats": top_lines(by_domain["cyber"]),
            "severity": highest,
        },
        "social_signals": {
            "summary": f"{len(by_domain['social'])} social signals captured.",
            "trending_topics": top_lines(by_domain["social"]),
            "severity": highest,
        },
        "confidence_note": (
            "Primary LLM providers were unavailable during this run: " + " | ".join(errors)
        ),
    }


def _throttle_gemini_requests(cfg: dict) -> None:
    """Enforce a minimum gap between Gemini calls to reduce burst rate limits."""
    min_interval = float(cfg.get("request_spacing_sec", 0.0))
    if min_interval <= 0:
        return

    global _LAST_GEMINI_REQUEST_TS
    now = time.time()
    elapsed = now - _LAST_GEMINI_REQUEST_TS
    if elapsed < min_interval:
        wait_for = min_interval - elapsed
        print(f"[llm] Throttling Gemini call for {wait_for:.1f}s to avoid rate limits...")
        time.sleep(wait_for)
    _LAST_GEMINI_REQUEST_TS = time.time()

'''
# Replacing this function.  commenting out till new code is validated.
def _generate_gemini(user_message: str, cfg: dict) -> Dict[str, Any]:
    import google.generativeai as genai

    api_key = get_secret("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in .env")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=SYSTEM_PROMPT,
    )
    response = model.generate_content(user_message)
    raw = response.text.strip()
    return _parse_json(raw)
'''

def _parse_json(raw: str) -> Dict[str, Any]:
    """Strip markdown fences if present and parse JSON."""
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1])
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[llm] JSON parse error: {e}")
        print(f"[llm] Raw response: {raw[:500]}")
        # Return a minimal fallback structure
        return {
            "executive_brief": "Intelligence digest generation encountered an error. Please check logs.",
            "market_pulse": {"summary": "Data unavailable.", "top_movers": [], "severity": "INFO"},
            "geopolitical_watch": {"summary": "Data unavailable.", "key_events": [], "severity": "INFO"},
            "cyber_threat_board": {"summary": "Data unavailable.", "top_threats": [], "severity": "INFO"},
            "social_signals": {"summary": "Data unavailable.", "trending_topics": [], "severity": "INFO"},
            "confidence_note": "Digest generation failed. Raw LLM output was not valid JSON.",
        }
