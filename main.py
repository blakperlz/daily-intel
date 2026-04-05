"""
daily-intel — entry point.

Usage:
  python main.py                     # Start the scheduler (daemon mode)
  python main.py --now daily         # Run a daily digest immediately
  python main.py --now weekly        # Run a weekly digest immediately
  python main.py --now daily --dry   # Dry run (no email sent)
"""
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        description="daily-intel: AI-powered intelligence digest platform"
    )
    parser.add_argument("--now", choices=["daily", "weekly"], metavar="TYPE",
                        help="Run a digest immediately (daily or weekly)")
    parser.add_argument("--dry", action="store_true",
                        help="Dry run — print digest without sending email")
    args = parser.parse_args()

    if args.now:
        from digest_runner import run_digest
        success = run_digest(digest_type=args.now, dry_run=args.dry)
        sys.exit(0 if success else 1)
    else:
        print("Starting daily-intel scheduler...")
        from scheduler import start_scheduler
        start_scheduler()


if __name__ == "__main__":
    main()
