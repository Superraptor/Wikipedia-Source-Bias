"""Pré-peuple le cache MariaDB avec le corpus démo.

Usage:
    DB_HOST=... DB_USER=... DB_PASSWORD=... DB_NAME=sourcesbias \
        python3 populate_cache.py
"""
import os
import sys
import time

from cache import Cache
from analyzer import normalize_analysis

CORPUS = [
    "https://fr.wikipedia.org/wiki/Emmanuel_Macron",
    "https://de.wikipedia.org/wiki/Angela_Merkel",
    "https://en.wikipedia.org/wiki/Brexit",
    "https://fr.wikipedia.org/wiki/Guerre_d%27Alg%C3%A9rie",
]


def main():
    try:
        import pymysql
    except ImportError:
        print("PyMySQL requis: pip install PyMySQL", file=sys.stderr)
        sys.exit(1)
    conn = pymysql.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", ""),
        database=os.environ.get("DB_NAME", "sourcesbias"),
        charset="utf8mb4",
    )
    with open("../toolforge/schema.sql", encoding="utf-8") as f:
        schema = f.read()
    cur = conn.cursor()
    for stmt in [s.strip() for s in schema.split(";") if s.strip()]:
        cur.execute(stmt)
    conn.commit()
    cur.close()

    cache = Cache(conn)
    try:
        from wikipedia_source_bias import analyze_url  # type: ignore
    except ImportError:
        from mock import mock_analysis
        analyze_url = mock_analysis  # type: ignore
        print("Repo amont manquant — utilisation du mock démo.", file=sys.stderr)

    for url in CORPUS:
        print(f"Analyzing {url}...", file=sys.stderr)
        try:
            raw = analyze_url(url)
            result = normalize_analysis(raw)
            cache.set(url, result)
            print(f"  cached: {result['source_count']} sources", file=sys.stderr)
        except Exception as e:
            print(f"  FAILED: {e}", file=sys.stderr)
        time.sleep(1.0)
    conn.close()


if __name__ == "__main__":
    main()
