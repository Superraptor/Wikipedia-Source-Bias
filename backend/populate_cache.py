"""Enqueue the demo corpus for analysis.

Queues the corpus URLs and lets backend/worker.py do the work, so this finishes
in milliseconds instead of holding a job open for the length of four full
scrapes. Pass --sync to analyze inline instead (useful locally with no worker).

    toolforge jobs run populate \
        --image tool-wikibias-analyzer/tool-wikibias-analyzer:latest \
        --command populate --wait
"""
import sys

import config
from cache import Cache
from runner import run_analysis

CORPUS = [
    "https://fr.wikipedia.org/wiki/Emmanuel_Macron",
    "https://de.wikipedia.org/wiki/Angela_Merkel",
    "https://en.wikipedia.org/wiki/Brexit",
    "https://fr.wikipedia.org/wiki/Guerre_d%27Alg%C3%A9rie",
]


def main(argv):
    sync = "--sync" in argv

    conn = config.connect()
    cache = Cache(conn)

    for url in CORPUS:
        if cache.get(url) is not None:
            print(f"already cached, skipping: {url}", file=sys.stderr)
            continue

        if not sync:
            cache.enqueue(url)
            print(f"queued: {url}", file=sys.stderr)
            continue

        print(f"analyzing {url} ...", file=sys.stderr)
        try:
            result = run_analysis(url)
        except Exception as e:
            print(f"  FAILED: {e}", file=sys.stderr)
            cache.mark_error(url, e)
            continue
        cache.set(url, result)
        print(f"  cached: {result.get('source_count')} sources", file=sys.stderr)

    conn.close()


if __name__ == "__main__":
    main(sys.argv[1:])
