"""
Social collector — Bluesky public API (no key required).
Uses the atproto SDK to search posts by keyword.
"""
from datetime import datetime
from typing import List

from collectors.base import BaseCollector
from models.intel_item import IntelItem, Domain, Severity
from utils.config_loader import get_config


class SocialCollector(BaseCollector):
    name = "social"

    def collect(self) -> List[IntelItem]:
        cfg = get_config()["collectors"]["social"]["bluesky"]
        if not cfg.get("enabled", True):
            return []

        keywords = cfg.get("keywords", [])
        max_posts = cfg.get("max_posts", 15)
        items = []
        items.extend(self._collect_bluesky(keywords, max_posts))
        return items

    def _collect_bluesky(self, keywords: list, max_posts: int) -> List[IntelItem]:
        items = []
        seen = set()

        try:
            from atproto import Client
            client = Client()
            # Public API — no auth required for search
            client.login("", "")  # anonymous session via public endpoint
        except Exception:
            # Fallback: use public HTTP API directly without atproto SDK auth
            return self._collect_bluesky_http(keywords, max_posts)

        for keyword in keywords[:5]:  # Cap keywords to avoid rate limits
            try:
                results = client.app.bsky.feed.search_posts({"q": keyword, "limit": 5})
                for post in getattr(results, "posts", []):
                    uri = getattr(post, "uri", "")
                    if uri in seen:
                        continue
                    seen.add(uri)

                    record = getattr(post, "record", None)
                    text = getattr(record, "text", "") if record else ""
                    author = getattr(getattr(post, "author", None), "handle", "unknown")
                    likes = getattr(post, "likeCount", 0) or 0

                    created_at = getattr(record, "createdAt", None)
                    try:
                        pub_date = datetime.fromisoformat(created_at.replace("Z", "+00:00")) if created_at else datetime.utcnow()
                    except Exception:
                        pub_date = datetime.utcnow()

                    post_id = uri.split("/")[-1] if uri else ""
                    bsky_url = f"https://bsky.app/profile/{author}/post/{post_id}" if author and post_id else "https://bsky.app"

                    items.append(IntelItem(
                        domain=Domain.SOCIAL,
                        source="Bluesky",
                        title=f"[{keyword}] @{author}: {text[:80]}",
                        summary=text[:500],
                        url=bsky_url,
                        published_at=pub_date,
                        severity=Severity.INFO,
                        tags=[keyword, "bluesky", "social"],
                        confidence=0.5,
                    ))
            except Exception as e:
                print(f"[social] Bluesky keyword '{keyword}' error: {e}")

        return items[:max_posts]

    def _collect_bluesky_http(self, keywords: list, max_posts: int) -> List[IntelItem]:
        """Fallback: direct HTTP to public Bluesky API."""
        import requests
        items = []
        seen = set()

        for keyword in keywords[:5]:
            try:
                resp = requests.get(
                    "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts",
                    params={"q": keyword, "limit": 5},
                    timeout=10,
                )
                resp.raise_for_status()
                posts = resp.json().get("posts", [])
                for post in posts:
                    uri = post.get("uri", "")
                    if uri in seen:
                        continue
                    seen.add(uri)

                    text = post.get("record", {}).get("text", "")
                    author = post.get("author", {}).get("handle", "unknown")
                    created_at = post.get("record", {}).get("createdAt", "")
                    try:
                        pub_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    except Exception:
                        pub_date = datetime.utcnow()

                    post_id = uri.split("/")[-1] if uri else ""
                    bsky_url = f"https://bsky.app/profile/{author}/post/{post_id}"

                    items.append(IntelItem(
                        domain=Domain.SOCIAL,
                        source="Bluesky",
                        title=f"[{keyword}] @{author}: {text[:80]}",
                        summary=text[:500],
                        url=bsky_url,
                        published_at=pub_date,
                        severity=Severity.INFO,
                        tags=[keyword, "bluesky", "social"],
                        confidence=0.5,
                    ))
            except Exception as e:
                print(f"[social] Bluesky HTTP keyword '{keyword}' error: {e}")

        return items[:max_posts]
