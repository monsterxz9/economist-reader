"""economist-reader CLI entry point.

Usage:
    uv run python cli.py                # process homepage articles
    uv run python cli.py --limit 1      # only first article
    uv run python cli.py --url URL      # specific article
    uv run python cli.py --dry-run      # scrape + dedup only, no AI/PDF/upload
"""
import argparse
import sys

from dotenv import load_dotenv

load_dotenv()

from econ import pipeline  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=20, help="max articles from homepage")
    ap.add_argument("--url", action="append", help="specific article URL (repeatable)")
    ap.add_argument("--dry-run", action="store_true", help="skip AI/PDF/upload")
    ap.add_argument("--no-upload", action="store_true", help="generate PDF locally, skip R2 upload")
    args = ap.parse_args()

    return pipeline.run(
        limit=args.limit,
        dry_run=args.dry_run,
        no_upload=args.no_upload,
        urls=args.url,
    )


if __name__ == "__main__":
    sys.exit(main())
