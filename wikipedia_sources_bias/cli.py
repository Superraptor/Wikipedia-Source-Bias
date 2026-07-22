from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse

from .analysis import analyze_page, render_report
from .map_sources import generate_source_map


def _sanitize_filename(title: str) -> str:
    # Remove characters that are generally forbidden/troublesome in filenames across systems
    cleaned = re.sub(r'[\\/*?:"<>|]', '_', title)
    # Replace spaces with underscores
    cleaned = cleaned.replace(" ", "_")
    # Replace consecutive underscores with a single underscore
    cleaned = re.sub(r'_+', '_', cleaned)
    # Strip leading/trailing underscores
    cleaned = cleaned.strip("_")
    # If the filename becomes empty, fallback to a safe name
    if not cleaned:
        cleaned = "unnamed_article"
    return cleaned.lower()


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze Wikipedia article sources and their biases")
    parser.add_argument("url", nargs="?", help="Wikipedia page URL")
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
    parser.add_argument(
        "--batch-file",
        help="Path to a text file containing article titles (one per line)",
    )
    parser.add_argument(
        "--prefix",
        default="en",
        help="Wikipedia language prefix (e.g., 'en', 'fr') (default: en)",
    )
    parser.add_argument(
        "--results-dir",
        default="results",
        help="Directory to save the batch results",
    )
    parser.add_argument(
        "--filter-unresolved",
        action="store_true",
        help="Filter out sources that do not resolve to a known country when building source maps",
    )
    parser.add_argument(
        "--split-multiple",
        action="store_true",
        help="Count each country and leaning individually when multiple are listed (e.g., 'Canada, United States')",
    )
    args = parser.parse_args()

    if not args.url and not args.batch_file:
        parser.error("must provide either a Wikipedia page URL or a --batch-file")

    max_sources = None if args.all else args.max_sources

    if args.batch_file:
        if not os.path.isfile(args.batch_file):
            print(f"Error: Batch file '{args.batch_file}' not found.", file=sys.stderr)
            sys.exit(1)
            
        try:
            with open(args.batch_file, "r", encoding="utf-8") as f:
                titles = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
        except Exception as e:
            print(f"Error reading batch file: {e}", file=sys.stderr)
            sys.exit(1)
            
        if not titles:
            print("Warning: No articles to process in batch file.", file=sys.stderr)
            return
            
        results_dir = args.results_dir
        os.makedirs(results_dir, exist_ok=True)
        
        success_count = 0
        total_count = len(titles)
        
        print(f"Starting batch processing of {total_count} articles...", file=sys.stderr)
        
        for idx, title in enumerate(titles, 1):
            print(f"[{idx}/{total_count}] Processing '{title}'...", file=sys.stderr)
            title_for_url = urllib.parse.quote(title.replace(" ", "_"))
            url = f"https://{args.prefix}.wikipedia.org/wiki/{title_for_url}"
            
            try:
                result = analyze_page(
                    url,
                    max_sources=max_sources,
                    no_cache=args.no_cache,
                    countries_only=args.countries_only,
                    skip_rate_limiting=args.skip_rate_limiting,
                    split_multiple=args.split_multiple
                )
                
                sanitized_title = _sanitize_filename(title)
                analysis_filename = os.path.join(results_dir, f"{sanitized_title}_analysis.json")
                with open(analysis_filename, "w", encoding="utf-8") as out_f:
                    json.dump(result, out_f, indent=2, ensure_ascii=False)
                    
                source_map = generate_source_map(
                    result,
                    filter_unresolved=args.filter_unresolved,
                    split_multiple=args.split_multiple
                )
                map_filename = os.path.join(results_dir, f"{sanitized_title}_map.json")
                with open(map_filename, "w", encoding="utf-8") as out_f:
                    json.dump(source_map, out_f, indent=2, ensure_ascii=False)
                    
                success_count += 1
                print(f"Successfully processed '{title}'. Saved to {analysis_filename} and {map_filename}.", file=sys.stderr)
            except Exception as e:
                print(f"Error processing '{title}': {e}", file=sys.stderr)
                
        print(f"Batch processing complete. Successfully processed {success_count}/{total_count} articles.", file=sys.stderr)
    else:
        try:
            result = analyze_page(
                args.url,
                max_sources=max_sources,
                no_cache=args.no_cache,
                countries_only=args.countries_only,
                skip_rate_limiting=args.skip_rate_limiting,
                split_multiple=args.split_multiple
            )
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
