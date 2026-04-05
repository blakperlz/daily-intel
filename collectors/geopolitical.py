"""
Geopolitical collector — GDELT GKG with two-layer country + keyword filter.
"""
from datetime import datetime, timedelta
from typing import List
import requests

from collectors.base import BaseCollector
from models.intel_item import IntelItem, Domain, Severity
from utils.config_loader import get_config

GDELT_COUNTRIES = {
    "US": "United States", "CN": "China", "RU": "Russia",
    "IR": "Iran", "KP": "North Korea", "UA": "Ukraine",
    "IL": "Israel", "TW": "Taiwan",
}

SEVERITY_MAP = {
    "CONFLICT": Severity.HIGH,
    "PROTEST": Severity.MEDIUM,
    "SANCTION": Severity.HIGH,
    "CYBER": Severity.HIGH,
    "MILITARY": Severity.HIGH,
    "DIPLOMATIC": Severity.MEDIUM,
}


class GeopoliticalCollector(BaseCollector):
    name = "geopolitical"

    def collect(self) -> List[IntelItem]:
        cfg = get_config()["collectors"]["geopolitical"]
        if not cfg.get("enabled", True):
            return []

        countries = cfg.get("countries", [])
        keywords = [k.lower() for k in cfg.get("keywords", [])]
        max_events = cfg.get("max_events", 20)

        items = []
        items.extend(self._collect_gdelt(countries, keywords, max_events))
        return items

    def _collect_gdelt(self, countries: list, keywords: list, max_events: int) -> List[IntelItem]:
        items = []
        try:
            # GDELT GKG API — search last 24h
            end_dt = datetime.utcnow()
            start_dt = end_dt - timedelta(hours=24)

            # Build keyword query for GDELT doc API
            kw_query = " OR ".join(f'"{kw}"' for kw in keywords[:5])  # GDELT limits query length
            country_filter = " OR ".join(f'sourcecountry:{c}' for c in countries)

            url = (
                f"https://api.gdeltproject.org/api/v2/doc/doc"
                f"?query={requests.utils.quote(kw_query)}"
                f"&mode=ArtList&maxrecords={max_events}"
                f"&format=json"
                f"&startdatetime={start_dt.strftime('%Y%m%d%H%M%S')}"
                f"&enddatetime={end_dt.strftime('%Y%m%d%H%M%S')}"
            )
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            articles = data.get("articles", [])
            seen_urls = set()

            for article in articles:
                art_url = article.get("url", "")
                if art_url in seen_urls:
                    continue
                seen_urls.add(art_url)

                title = article.get("title", "No title")
                title_lower = title.lower()

                # Layer 2: keyword filter on title
                matched_kw = [kw for kw in keywords if kw in title_lower]
                if not matched_kw:
                    continue

                pub_str = article.get("seendate", "")
                try:
                    pub_date = datetime.strptime(pub_str, "%Y%m%dT%H%M%SZ")
                except Exception:
                    pub_date = datetime.utcnow()

                domain_tags = article.get("domain", "")
                source_name = domain_tags.split(".")[0].capitalize() if domain_tags else "GDELT"

                items.append(IntelItem(
                    domain=Domain.GEOPOLITICAL,
                    source=f"GDELT/{source_name}",
                    title=title,
                    summary=f"{title}. Matched signals: {', '.join(matched_kw)}.",
                    url=art_url or "https://gdeltproject.org",
                    published_at=pub_date,
                    severity=Severity.HIGH if any(k in ["cyberattack", "coup", "airstrike", "invasion"] for k in matched_kw) else Severity.MEDIUM,
                    tags=matched_kw + ["geopolitical", "GDELT"],
                    confidence=0.7,
                ))

        except Exception as e:
            print(f"[geopolitical] GDELT error: {e}")

        return items[:max_events]
