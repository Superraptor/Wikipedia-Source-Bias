import os
import sys
from urllib.parse import urlparse, unquote

from flask import Flask, request, jsonify, send_from_directory, render_template

import config
from cache import Cache, PENDING, RUNNING, DONE, ERROR
from runner import run_analysis, AnalysisUnavailable

# The Nuxt SPA is generated into backend/static at build time (see the root
# package.json). In production Flask serves both the bundle and /api from the
# same origin -- the nitro `routeRules` proxy in nuxt.config.ts only exists
# during `nuxt dev` and is absent from a static `nuxt generate` build.
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

# static_folder=None on purpose: mounting Flask's built-in static handler at ""
# registers a `/<path:filename>` rule that shadows the SPA catch-all below, so
# unknown /api/* paths would fall into the static handler and return a bare
# HTML 404 instead of JSON. The spa() view does the file serving itself.
app = Flask(__name__, static_folder=None)

# Analyses take minutes, far longer than a request may live. On Toolforge the
# work is handed to backend/worker.py; locally, where no worker runs, doing it
# inline keeps the dev loop simple.
SYNC_ANALYSIS = os.environ.get(
    "SYNC_ANALYSIS", "0" if config.on_toolforge() else "1"
).strip().lower() in ("1", "true", "yes", "on")


# In sync mode the web process runs analyses itself, so it needs the shared
# lookup caches too. In async mode (Toolforge) the worker does the analysing,
# but installing here as well keeps behaviour identical if SYNC_ANALYSIS is
# ever turned on.
if config.on_toolforge() or os.environ.get("USE_DB_CACHESTORE"):
    try:
        import db_cachestore

        db_cachestore.install(config.connect)
    except Exception as _e:  # pragma: no cover - never block startup on this
        print(f"Could not install ToolsDB cache store: {_e}", file=sys.stderr)


def _db_conn():
    return config.connect()


def get_cache():
    return Cache(_db_conn())


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/healthz")
def healthz():
    """Liveness probe target for `toolforge webservice --health-check-path`."""
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

        status, err = cache.status_of(url)
        if status in (PENDING, RUNNING):
            return jsonify({"status": PENDING, "page_url": url}), 202
        if status == ERROR and not SYNC_ANALYSIS:
            return jsonify({"error": err or "Analysis failed"}), 500

    if not SYNC_ANALYSIS:
        if cache is None:
            return jsonify({"error": "Cache unavailable, cannot queue analysis"}), 503
        cache.enqueue(url)
        return jsonify({"status": PENDING, "page_url": url}), 202

    try:
        result = run_analysis(url)
    except AnalysisUnavailable as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {e}"}), 500

    if cache is not None:
        try:
            cache.set(url, result)
        except Exception:
            pass
    return jsonify(result)


@app.route("/api/status")
def api_status():
    """Queue introspection: what is pending, running, done or failed."""
    try:
        cache = get_cache()
    except Exception as e:
        return jsonify({"error": f"Cache unavailable: {e}"}), 503
    return jsonify(
        {
            "counts": cache.queue_stats(),
            "sync_analysis": SYNC_ANALYSIS,
            "recent": [_decorate(r) for r in cache.recent(50)],
        }
    )


def _display_title(row):
    """A readable name for a queue row.

    `page_title` is only written when an analysis completes, so pending and
    running rows had none and fell back to the raw URL -- which is why the
    status table mixed titles and URLs. Derive one from the URL instead, so
    every row reads the same way.
    """
    title = row.get("page_title")
    if title:
        return title
    url = row.get("page_url") or ""
    slug = unquote(urlparse(url).path.rsplit("/", 1)[-1])
    return slug.replace("_", " ") or url


def _humanize(seconds):
    """'3 min 12 s' style duration. None when unknown."""
    if seconds is None:
        return None
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"{seconds} s"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes} min {sec:02d} s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours} h {minutes:02d} min"


def _decorate(row):
    """Add the presentation fields the status view needs."""
    row["display_title"] = _display_title(row)
    # A running row's clock started when a worker claimed it (updated_at); a
    # waiting row's when it was queued (created_at).
    if row["status"] == RUNNING:
        row["duration"] = _humanize(row.get("since_update_seconds"))
        row["duration_label"] = "en cours depuis"
    elif row["status"] == PENDING:
        row["duration"] = _humanize(row.get("age_seconds"))
        row["duration_label"] = "en attente depuis"
    else:
        row["duration"] = _humanize(row.get("since_update_seconds"))
        row["duration_label"] = "il y a"
    return row


@app.route("/status")
def status_page():
    """Small server-rendered status view.

    Deliberately plain HTML rather than a Nuxt route: it has to stay readable
    when the SPA bundle or the queue itself is broken, which is exactly when
    someone goes looking for it.
    """
    try:
        cache = get_cache()
        counts = cache.queue_stats()
        rows = cache.recent(50)
        rows = [_decorate(r) for r in rows]
        err = None
    except Exception as e:
        counts, rows, err = {}, [], str(e)

    return render_template(
        "status.html",
        counts=counts,
        rows=rows,
        db_error=err,
        total=sum(counts.values()),
        sync=SYNC_ANALYSIS,
    )


@app.route("/robots.txt")
def robots():
    # Toolforge's shared proxy serves a deny-all robots.txt when a tool 404s
    # this path, so an explicit one is required to be indexable at all.
    return app.response_class(
        "User-agent: *\nAllow: /\nDisallow: /api/\n", mimetype="text/plain"
    )


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def spa(path):
    """Serve the built SPA, falling back to index.html for client-side routes."""
    if path.startswith("api/"):
        return jsonify({"error": "Not found"}), 404

    full = os.path.join(STATIC_DIR, path)
    if path and os.path.isfile(full):
        return send_from_directory(STATIC_DIR, path)

    index = os.path.join(STATIC_DIR, "index.html")
    if not os.path.isfile(index):
        return (
            jsonify(
                {
                    "error": "Frontend bundle missing. Run `npm run build` at the "
                    "repo root to generate backend/static."
                }
            ),
            503,
        )
    return send_from_directory(STATIC_DIR, "index.html")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
