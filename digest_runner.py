"""
Digest runner — orchestrates collection → LLM → email for one run.
Called by the scheduler or directly via CLI: python digest_runner.py --type daily
"""
import argparse
import sys
import time
from datetime import datetime
from typing import List

from collectors import (
    FinancialCollector,
    CyberCollector,
    GeopoliticalCollector,
    SocialCollector,
    RSSCollector,
    DarkWebCollector,
)
from llm import generate_digest
from mailer.sender import send_digest
from models.intel_item import IntelItem
from utils.output_writer import save_digest


def run_all_collectors() -> List[IntelItem]:
    """Run all enabled collectors and return merged IntelItem list."""
    collectors = [
        FinancialCollector(),
        CyberCollector(),
        GeopoliticalCollector(),
        SocialCollector(),
        RSSCollector(),
        DarkWebCollector(),
    ]

    all_items = []
    for collector in collectors:
        items = collector.safe_collect()
        all_items.extend(items)

    # Sort by severity then recency
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    all_items.sort(key=lambda x: (
        severity_order.get(x.severity.value, 5),
        -(x.published_at.timestamp() if x.published_at else 0),
    ))

    print(f"[runner] Total items collected: {len(all_items)}")
    return all_items


def run_digest(digest_type: str = "daily", dry_run: bool = False) -> bool:
    """
    Full pipeline: collect → generate → send.
    dry_run=True prints the digest JSON without sending email.
    """
    start = time.time()
    print(f"\n[runner] Starting {digest_type} digest at {datetime.utcnow().isoformat()}")

    # 1. Collect
    items = run_all_collectors()
    if not items:
        print("[runner] No items collected — aborting digest.")
        return False

    # 2. Generate
    print(f"[runner] Generating {digest_type} digest with {len(items)} items...")
    digest = generate_digest(items, digest_type=digest_type)

    if dry_run:
        import json
        print("\n[DRY RUN] Digest output:")
        print(json.dumps(digest, indent=2))
        print(f"\n[runner] Dry run complete in {time.time() - start:.1f}s")
        return True

    # 3. Save to repo
    save_digest(digest, digest_type=digest_type, item_count=len(items))

    # 4. Send email
    print("[runner] Sending digest...")
    send_digest(digest, digest_type=digest_type, item_count=len(items))

    elapsed = time.time() - start
    print(f"[runner] Done in {elapsed:.1f}s")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a daily-intel digest")
    parser.add_argument("--type", choices=["daily", "weekly"], default="daily",
                        help="Type of digest to run (default: daily)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print digest JSON without sending email")
    args = parser.parse_args()

    success = run_digest(digest_type=args.type, dry_run=args.dry_run)
    sys.exit(0 if success else 1)
