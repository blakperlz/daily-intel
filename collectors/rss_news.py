"""
RSS/News collector — feedparser + optional NewsAPI free tier.
"""
from datetime import datetime
from typing import List
import feedparser

from collectors.base import BaseCollector
from models.intel_item import IntelItem, Domain, Severity
from utils.config_loader import get_config

# Simple keyword-to-domain mapping for auto-tagging RSS items
CYBER_KEYWORDS = {"cve", "vulnerability", "breach", "ransomware", "malware", "exploit", "patch", "zero-day", "threat"}
GEO_KEYWORDS = {"sanction", "coup", "war", "conflict", "airstrike", "missile", "invasion", "military", "nuclear"}


def _classify_domain(title: str, summary: str) -> Domain:
    text = (title + " " + summary).lower()
    if any(kw in text for kw in CYBER_KEYWORDS):
        return Domain.CYBER
    if any(kw in text for kw in GEO_KEYWORDS):
        return Domain.GEOPOLITICAL
    return Domain.GEOPOLITICAL  # Default news to geo for now


class RSSCollector(BaseCollector):
    name = "rss"

    def collect(self) -> List[IntelItem]:
        cfg = get_config()["collectors"]["rss"]
        if not cfg.get("enabled", True):
            return []

        items = []
        max_per_feed = cfg.get("max_items_per_feed", 5)

        for feed_cfg in cfg.get("feeds", []):
            items.extend(self._parse_feed(feed_cfg["name"], feed_cfg["url"], max_per_feed))

        return items

    def _parse_feed(self, feed_name: str, url: str, max_items: int) -> List[IntelItem]:
        items = []
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:max_items]:
                title = entry.get("title", "No title")
                summary = entry.get("summary", entry.get("description", title))
                # Strip HTML tags from summary
                import re
                summary = re.sub(r"<[^>]+>", "", summary)[:600]

                link = entry.get("link", url)

                pub_parsed = entry.get("published_parsed")
                if pub_parsed:
                    pub_date = datetime(*pub_parsed[:6])
                else:
                    pub_date = datetime.utcnow()

                domain = _classify_domain(title, summary)

                items.append(IntelItem(
                    domain=domain,
                    source=feed_name,
                    title=title,
                    summary=summary,
                    url=link,
                    published_at=pub_date,
                    severity=Severity.MEDIUM,
                    tags=[feed_name.lower(), "news", "rss"],
                    confidence=0.75,
                ))
        except Exception as e:
            print(f"[rss] Feed '{feed_name}' error: {e}")
        return items
