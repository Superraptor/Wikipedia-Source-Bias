import os
from flask import Flask, request, jsonify
from cache import Cache
from analyzer import normalize_analysis

app = Flask(__name__)


def _db_conn():
    import pymysql
    return pymysql.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", ""),
        database=os.environ.get("DB_NAME", "sourcesbias"),
        charset="utf8mb4",
        autocommit=False,
    )


def get_cache():
    return Cache(_db_conn())


def run_analysis(url):
    """Appelle le repo amont Wikipedia-Source-Bias et normalise la sortie.

    En l'absence du repo amont installé, utilise un mock démo (backend/mock.py)
    pour que le frontend puisse rendre le dashboard. Sur Toolforge avec le repo
    amont installé + cache pré-populé, le vrai flow est utilisé.
    """
    try:
        from wikipedia_sources_bias import analyze_page  # type: ignore
        raw = analyze_page(url)
    except ImportError:
        from mock import mock_analysis
        raw = mock_analysis(url)
    return normalize_analysis(raw)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/analyze")
def analyze():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "Missing 'url' query parameter"}), 400
    try:
        cache = get_cache()
    except Exception:
        cache = None
    if cache is not None:
        cached = cache.get(url)
        if cached is not None:
            return jsonify(cached)
    try:
        result = run_analysis(url)
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {e}"}), 500
    if cache is not None:
        try:
            cache.set(url, result)
        except Exception:
            pass
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
