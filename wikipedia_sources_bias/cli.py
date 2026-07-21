from __future__ import annotations

import argparse
import json

from .analysis import analyze_page


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze Wikipedia article sources")
    parser.add_argument("url", help="Wikipedia page URL")
    args = parser.parse_args()

    result = analyze_page(args.url)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
