from __future__ import annotations

import argparse
import json
import sys

from .analysis import analyze_page, render_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze Wikipedia article sources and their biases")
    parser.add_argument("url", help="Wikipedia page URL")
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--max-sources",
        type=int,
        default=10,
        help="Maximum number of sources to analyze (default: 10)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Analyze all sources on the page (overrides --max-sources)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass page cache and force fresh analysis",
    )
    parser.add_argument(
        "--countries-only",
        action="store_true",
        help="Only extract and summarize the countries for each source (much faster)",
    )
    parser.add_argument(
        "--skip-rate-limiting",
        action="store_true",
        help="Bypass all sleep delays and external rate-limited lookups",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="File path to write output to",
    )
    args = parser.parse_args()

    max_sources = None if args.all else args.max_sources
    try:
        result = analyze_page(args.url, max_sources=max_sources, no_cache=args.no_cache, countries_only=args.countries_only, skip_rate_limiting=args.skip_rate_limiting)
    except Exception as e:
        print(f"Error during analysis: {e}", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        output_str = json.dumps(result, indent=2, ensure_ascii=False)
    else:
        output_str = render_report(result)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_str)
            print(f"Report successfully saved to: {args.output}")
        except Exception as e:
            print(f"Failed to write to file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output_str)


if __name__ == "__main__":
    main()
