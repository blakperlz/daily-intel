"""
LLM digest generator.
Primary: Claude Haiku. Fallback: Gemini 1.5 Flash.
Model-agnostic via config.yaml provider setting.
"""
import json
import os
from typing import List, Dict, Any

from models.intel_item import IntelItem
from utils.config_loader import get_config, get_secret
from llm.prompts import SYSTEM_PROMPT, DIGEST_PROMPT, WEEKLY_PROMPT


def generate_digest(items: List[IntelItem], digest_type: str = "daily") -> Dict[str, Any]:
    """
    Generate a structured digest from a list of IntelItems.
    digest_type: "daily" | "weekly"
    Returns parsed JSON dict.
    """
    cfg = get_config()["llm"]
    provider = cfg.get("provider", "claude")

    # Serialize intel items for the prompt
    intel_data = [item.to_dict() for item in items]
    intel_json = json.dumps(intel_data, indent=2, default=str)

    prompt_template = WEEKLY_PROMPT if digest_type == "weekly" else DIGEST_PROMPT
    user_message = prompt_template.format(intel_json=intel_json)

    if provider == "claude":
        return _generate_claude(user_message, cfg)
    elif provider == "gemini":
        return _generate_gemini(user_message, cfg)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


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
