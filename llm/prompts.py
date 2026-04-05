"""
Prompt templates for digest generation.
All prompts use Bloomberg-style analyst persona: direct, factual, no fluff.
"""

SYSTEM_PROMPT = """You are a senior intelligence analyst writing a daily briefing for a small group of investors and security professionals.

Your style is Bloomberg Terminal meets CIA World Intelligence Review: direct, factual, no filler. Every sentence earns its place.

Rules:
- Lead with the most important signal in each section
- Use exact numbers when available (prices, CVE IDs, CVSS scores, percentages)
- Flag severity explicitly: CRITICAL / HIGH / MEDIUM
- Cite the source inline (e.g., "per CISA KEV", "via NVD", "on Bluesky")
- Never speculate beyond the data provided
- Output ONLY valid JSON — no markdown, no preamble
"""

DIGEST_PROMPT = """Analyze the following intelligence items collected in the last 24 hours and produce a structured daily briefing.

INTEL ITEMS:
{intel_json}

Produce a JSON object with this exact structure:
{{
  "executive_brief": "3-5 sentence situational summary covering the top signals across all domains. Lead with the highest severity item.",
  "market_pulse": {{
    "summary": "2-3 sentence market overview with specific numbers",
    "top_movers": ["list of up to 5 notable price moves or macro events"],
    "severity": "HIGH | MEDIUM | LOW"
  }},
  "geopolitical_watch": {{
    "summary": "2-3 sentence geopolitical overview",
    "key_events": ["list of up to 5 notable events"],
    "severity": "HIGH | MEDIUM | LOW"
  }},
  "cyber_threat_board": {{
    "summary": "2-3 sentence cyber overview",
    "top_threats": ["list of up to 5 CVEs, KEV entries, or breach signals with IDs and severity"],
    "severity": "HIGH | MEDIUM | LOW"
  }},
  "social_signals": {{
    "summary": "1-2 sentence overview of trending narratives on Bluesky",
    "trending_topics": ["list of up to 3 trending topics with signal strength"],
    "severity": "LOW | INFO"
  }},
  "confidence_note": "One sentence noting any data gaps or low-confidence signals in this brief."
}}"""

WEEKLY_PROMPT = """Analyze the following intelligence items collected over the past 7 days and produce a comprehensive weekly intelligence summary.

INTEL ITEMS:
{intel_json}

Produce a JSON object with this exact structure:
{{
  "week_in_review": "4-6 sentence narrative covering the dominant themes and how they evolved across the week",
  "market_pulse": {{
    "summary": "3-4 sentence weekly market overview with specific numbers and trends",
    "notable_moves": ["list of up to 7 notable price moves, macro events, or earnings"],
    "outlook": "1 sentence forward-looking note based on current signals"
  }},
  "geopolitical_watch": {{
    "summary": "3-4 sentence geopolitical overview of the week",
    "key_developments": ["list of up to 7 notable events in order of importance"],
    "escalation_risks": ["list of up to 3 situations to monitor"]
  }},
  "cyber_threat_board": {{
    "summary": "3-4 sentence cyber threat overview",
    "top_vulnerabilities": ["list of up to 7 CVEs/KEV entries with CVSS scores"],
    "threat_actor_activity": "1-2 sentences on notable threat actor activity if any"
  }},
  "social_signals": {{
    "summary": "2 sentence overview of dominant narratives across the week",
    "trending_topics": ["list of up to 5 topics with trajectory notes"]
  }},
  "next_week_watchlist": ["list of 3-5 situations, events, or data releases to monitor next week"],
  "confidence_note": "One sentence noting data gaps or caveats."
}}"""
