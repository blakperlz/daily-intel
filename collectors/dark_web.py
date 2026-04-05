"""
Dark web collector — safe proxy approach only.
Uses Ahmia.fi (HTTPS, no Tor) for indexed .onion content signals.
No direct Tor connections. Ever.
"""
from datetime import datetime
from typing import List
import requests
from bs4 import BeautifulSoup

from collectors.base import BaseCollector
from models.intel_item import IntelItem, Domain, Severity
from utils.config_loader import get_config


class DarkWebCollector(BaseCollector):
    name = "dark_web"

    def collect(self) -> List[IntelItem]:
        cfg = get_config().get("dark_web", {}).get("ahmia", {})
        if not cfg.get("enabled", False):
            return []

        keywords = cfg.get("keywords", [])
        max_results = cfg.get("max_results", 5)
        items = []

        for keyword in keywords[:3]:  # Limit to 3 keywords to be respectful of Ahmia
            items.extend(self._search_ahmia(keyword, max_results))

        return items

    def _search_ahmia(self, keyword: str, max_results: int) -> List[IntelItem]:
        items = []
        try:
            resp = requests.get(
                "https://ahmia.fi/search/",
                params={"q": keyword},
                headers={"User-Agent": "daily-intel/1.0 (OSINT research tool)"},
                timeout=15,
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            results = soup.select("li.result")[:max_results]
            for result in results:
                title_el = result.select_one("h4")
                desc_el = result.select_one("p.description")
                link_el = result.select_one("cite")

                title = title_el.get_text(strip=True) if title_el else "Dark web signal"
                desc = desc_el.get_text(strip=True) if desc_el else "No description available."
                onion_ref = link_el.get_text(strip=True) if link_el else "ahmia.fi"

                items.append(IntelItem(
                    domain=Domain.CYBER,
                    source="Ahmia.fi",
                    title=f"[Dark Web Signal] {title[:80]}",
                    summary=f"Keyword '{keyword}' matched indexed dark web content: {desc[:400]}",
                    url="https://ahmia.fi/search/?q=" + requests.utils.quote(keyword),
                    published_at=datetime.utcnow(),
                    severity=Severity.HIGH,
                    tags=[keyword, "dark web", "ahmia", "OSINT"],
                    confidence=0.5,
                ))
        except Exception as e:
            print(f"[dark_web] Ahmia '{keyword}' error: {e}")
        return items
