import os
import re
import sys
from urllib.parse import urlparse, unquote, quote

from flask import Flask, request, jsonify, send_from_directory, render_template

import config
from cache import Cache, PENDING, RUNNING, DONE, ERROR
from runner import run_analysis, AnalysisUnavailable
from analyzer import normalize_analysis
from wikipedia_sources_bias.analysis import ArticleNotFound
from wikipedia_sources_bias.provenance import METHOD_VERSION
import status_i18n
from invariants import check_analysis, INVARIANTS

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
            # Re-normalise on READ, not just at analysis time. Normalisation is
            # cheap presentation logic (region derivation, unmapped markers,
            # derived aggregate fields), so applying it here means a fix to it
            # reaches every stored analysis immediately instead of only those
            # re-scraped afterwards. It is idempotent: every field it writes is
            # a field it reads.
            return jsonify(normalize_analysis(cached))

        status, err = cache.status_of(url)
        if status in (PENDING, RUNNING):
            # Tell the caller what is actually happening. A bare "pending"
            # left users unable to tell a long analysis from a dead one.
            body = {"status": PENDING, "page_url": url, "queue_state": status}
            # Best-effort: the 202 is still correct without the detail.
            try:
                row = cache.row_for(url)
            except Exception:
                row = None
            if row:
                info = _decorate(row)
                body.update(
                    progress_done=info.get("progress_done"),
                    progress_total=info.get("progress_total"),
                    progress_pct=info.get("progress_pct"),
                    stage=info.get("stage"),
                    eta=info.get("eta"),
                    health=info.get("health"),
                    quiet_for=info.get("quiet_for"),
                )
                try:
                    body["queue_position"] = cache.queue_position(url)
                except Exception:
                    pass
            return jsonify(body), 202
        if status == ERROR and not SYNC_ANALYSIS:
            # A missing article is a 404 with a code the UI can translate, not
            # a generic 500 with a stack-flavoured string.
            if (err or "").startswith(NOT_FOUND_MARKER):
                return jsonify({
                    "error": err[len(NOT_FOUND_MARKER):].lstrip(": ").strip(),
                    "code": "article_not_found",
                }), 404
            return jsonify({"error": err or "Analysis failed"}), 500

    if not SYNC_ANALYSIS:
        if cache is None:
            return jsonify({"error": "Cache unavailable, cannot queue analysis"}), 503
        cache.enqueue(url)
        return jsonify({"status": PENDING, "page_url": url}), 202

    try:
        result = run_analysis(url)
    except ArticleNotFound as e:
        return jsonify({"error": str(e), "code": "article_not_found"}), 404
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
    # page_title comes from the analyzer as the raw last path segment, so it
    # is still percent-encoded ("V%C3%A9lo"). Decode it the same way as the
    # URL-derived fallback rather than trusting it to be display-ready.
    title = row.get("page_title")
    if not title:
        title = urlparse(row.get("page_url") or "").path.rsplit("/", 1)[-1]
    return unquote(title).replace("_", " ") or (row.get("page_url") or "")


def _humanize(seconds, t=None):
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


STAGE_KEYS = {"sources": "stageSources", "aggregating": "stageAggregating"}


def _coarse(seconds, t=None):
    """Round an ETA so it stops twitching between refreshes.

    A precise number that changes every 15s reads as unreliable even when the
    underlying estimate is fine, so buckets get wider as the estimate grows.
    """
    if seconds is None:
        return None
    seconds = max(0, int(seconds))
    if seconds < 60:
        return t("underMinute") if t else "moins d'une minute"
    minutes = seconds / 60
    if minutes < 10:
        return f"~{int(round(minutes))} min"
    if minutes < 60:
        return f"~{int(round(minutes / 5) * 5)} min"
    hours = minutes / 60
    if hours < 4:
        return f"~{hours:.1f} h".replace(".0 h", " h")
    return f"~{int(round(hours))} h"


def _progress(row, t=None):
    """Percent complete plus an ETA.

    The ETA comes from the worker, which measures how long each source
    actually took and smooths it with an EWMA. Earlier this was derived here
    from "time since queued" divided by sources done -- that counted queue
    wait as analysis time and used a cumulative mean, so the estimate climbed
    steadily whenever later sources were slower. The web tier now only ages
    the worker's figure by the time since it was written.
    """
    done = row.get("progress_done")
    total = row.get("progress_total")
    if not total or done is None:
        return None, None, None

    pct = min(100, int(done * 100 / total))

    eta_seconds = row.get("eta_seconds")
    if eta_seconds is None:
        # No worker estimate yet: fall back to this run's own throughput,
        # using running_seconds (analysis time) rather than age (queue + analysis).
        running = row.get("running_seconds")
        if running and done > 0 and done < total:
            eta_seconds = int((running / done) * (total - done))
    else:
        # Count down between progress writes instead of showing a stale number.
        eta_seconds = max(0, int(eta_seconds) - int(row.get("since_update_seconds") or 0))

    return pct, f"{done}/{total}", _coarse(eta_seconds, t)


# A running analysis writes progress every ~5s. Silence for much longer means
# the worker died mid-source: the row is still 'running' but nothing is
# happening, and the stale sweep will reclaim it. Distinguishing that from
# "large article, working fine" is the difference between waiting patiently
# and assuming the tool is broken.
STALL_SECONDS = 180

# Prefix the worker writes into `error` for a missing Wikipedia article.
NOT_FOUND_MARKER = "ARTICLE_NOT_FOUND"


def _health(row):
    """'working' | 'stalled' | None (not running)."""
    if row.get("status") != RUNNING:
        return None
    quiet = row.get("since_update_seconds")
    if quiet is not None and quiet > STALL_SECONDS:
        return "stalled"
    return "working"


# <lang>.wikipedia.org / <lang>.m.wikipedia.org
_WIKI_HOST = re.compile(r"^([a-z][a-z0-9-]*)\.(?:m\.)?wikipedia\.org$", re.I)


def _analysis_url(row):
    """Link to this tool's own dashboard for the article, not to Wikipedia.

    Mirrors Wikipedia's own shape (/wikipedia/fr/Brexit) rather than the old
    /article/<title>?src=<whole url percent-encoded> form.
    """
    url = row.get("page_url") or ""
    parts = urlparse(url)
    slug = parts.path.rsplit("/", 1)[-1]
    if not slug:
        return None
    host = _WIKI_HOST.match(parts.netloc or "")
    if host and parts.path.startswith("/wiki/"):
        # Explicitly versioned: /v1 and /v2 are the only article shapes.
        return f"/v1/wikipedia/{host.group(1).lower()}/{slug}"
    return f"/article/{slug}?src={quote(url, safe='')}"


def _decorate(row, t=None):
    """Add the presentation fields the status view needs."""
    t = t or status_i18n.translator(status_i18n.DEFAULT)
    row["display_title"] = _display_title(row)
    row["analysis_url"] = _analysis_url(row)
    pct, counted, eta = _progress(row, t)
    row["progress_pct"] = pct
    row["progress_text"] = counted
    row["eta"] = eta
    stage_key = STAGE_KEYS.get(row.get("stage"))
    row["stage_label"] = t(stage_key) if stage_key else row.get("stage")
    row["health"] = _health(row)
    row["quiet_for"] = _humanize(row.get("since_update_seconds"), t) \
        if row.get("status") == RUNNING else None
    # TOTAL elapsed, not time-since-last-step. `since_update_seconds` resets on
    # every progress write, so using it made a long analysis look like it had
    # only just started.
    if row["status"] == RUNNING:
        # Since a worker claimed it, excluding the queue wait.
        row["duration"] = _humanize(row.get("running_seconds"), t)
        row["duration_label"] = t("durRunning")
    elif row["status"] == PENDING:
        row["duration"] = _humanize(row.get("age_seconds"), t)
        row["duration_label"] = t("durPending")
    else:
        # Finished: how long the run actually took, start to finish.
        row["duration"] = _humanize(row.get("total_seconds"), t)
        row["duration_label"] = t("durTotal")
    return row


@app.route("/status")
def status_page():
    """Small server-rendered status view.

    Deliberately plain HTML rather than a Nuxt route: it has to stay readable
    when the SPA bundle or the queue itself is broken, which is exactly when
    someone goes looking for it.
    """
    locale = status_i18n.pick_locale(request)
    t = status_i18n.translator(locale)
    try:
        cache = get_cache()
        counts = cache.queue_stats()
        rows = [_decorate(r, t) for r in cache.recent(50)]
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
        t=t,
        locale=locale,
    )


def _audit_all(cache, limit=200):
    """Run every invariant over every stored analysis."""
    rows = cache.recent(limit)
    done = [r for r in rows if r.get("status") == "done"]
    results, failures = [], []
    for row in done:
        payload = cache.get(row["page_url"])
        if payload is None:
            continue
        payload = normalize_analysis(payload)
        payload.setdefault("revision_id", row.get("revision_id"))
        payload.setdefault("method_version", row.get("method_version"))
        found = check_analysis(payload)
        results.append({
            "page_url": row["page_url"],
            "title": _display_title(row),
            "analysis_url": _analysis_url(row),
            "revision_id": row.get("revision_id"),
            "method_version": row.get("method_version"),
            "passed": len(INVARIANTS) - len({n for n, _ in found}),
            "total": len(INVARIANTS),
            "failures": found,
        })
        failures.extend((row["page_url"], n, msg) for n, msg in found)
    return results, failures


@app.route("/api/audit")
def api_audit():
    """Machine-readable version of the public audit."""
    try:
        cache = get_cache()
    except Exception as e:
        return jsonify({"error": f"Cache unavailable: {e}"}), 503
    results, failures = _audit_all(cache)
    by_invariant = {}
    for _url, name, _msg in failures:
        by_invariant[name] = by_invariant.get(name, 0) + 1
    return jsonify({
        "invariants": [{"name": n, "description": d} for n, d in INVARIANTS],
        "analyses_checked": len(results),
        "analyses_clean": sum(1 for r in results if not r["failures"]),
        "failures_by_invariant": by_invariant,
        "results": results,
    })


@app.route("/audit")
def audit_page():
    """Published self-check.

    A tool that only publishes its results asks to be trusted. Publishing the
    checks -- and the ones currently failing -- makes it criticisable instead.
    """
    locale = status_i18n.pick_locale(request)
    t = status_i18n.translator(locale)
    try:
        cache = get_cache()
        results, failures = _audit_all(cache)
        err = None
    except Exception as e:
        results, failures, err = [], [], str(e)

    by_invariant = {}
    for _url, name, _msg in failures:
        by_invariant.setdefault(name, []).append(_msg)

    return render_template(
        "audit.html",
        t=t,
        locale=locale,
        db_error=err,
        invariants=INVARIANTS,
        by_invariant=by_invariant,
        results=results,
        checked=len(results),
        clean=sum(1 for r in results if not r["failures"]),
        method_version=METHOD_VERSION,
    )


@app.route("/api/reference")
def api_reference():
    """Every judgement the tool itself asserts, in one place.

    These were 267 statements buried in .py files: which domain belongs to
    which country, which TLD implies which country, which country sits in
    which region. A tool that audits sourcing should not hide its own.
    """
    from wikipedia_sources_bias.heuristics_data import (
        DOMAIN_BIAS_DATABASE, TLD_GEOGRAPHY_MAP,
    )
    from analyzer import REGION_MAP

    return jsonify({
        "method_version": METHOD_VERSION,
        "note": (
            "The curated domain table deliberately asserts NO political "
            "leaning. Leaning comes only from Wikidata (P1387) or Media "
            "Bias/Fact Check, and is 'unknown' when neither has an opinion."
        ),
        "curated_domains": {
            k: dict(v) for k, v in sorted(DOMAIN_BIAS_DATABASE.items())
        },
        "tld_to_country": {
            k: {"country": v[0], "region": v[1]}
            for k, v in sorted(TLD_GEOGRAPHY_MAP.items())
        },
        "country_to_region": dict(sorted(REGION_MAP.items())),
    })


@app.route("/robots.txt")
def robots():
    # Toolforge's shared proxy serves a deny-all robots.txt when a tool 404s
    # this path, so an explicit one is required to be indexable at all.
    return app.response_class(
        "User-agent: *\nAllow: /\nDisallow: /api/\n", mimetype="text/plain"
    )


# Nuxt fingerprints everything under /_nuxt/ with a content hash, so those
# files are immutable and can be cached hard. index.html must NOT be: it names
# those hashed chunks, and a stale copy points at chunks a redeploy has already
# replaced. The browser then requests a chunk that no longer exists, the SPA
# fallback answers with index.html, and the module loader fails on the MIME
# type -- a blank page for every returning visitor after each deploy.
IMMUTABLE_PREFIX = "_nuxt/"
IMMUTABLE_CACHE = "public, max-age=31536000, immutable"
HTML_CACHE = "no-cache, must-revalidate"


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def spa(path):
    """Serve the built SPA, falling back to index.html for client-side routes."""
    if path.startswith("api/"):
        return jsonify({"error": "Not found"}), 404

    full = os.path.join(STATIC_DIR, path)
    if path and os.path.isfile(full):
        resp = send_from_directory(STATIC_DIR, path)
        resp.headers["Cache-Control"] = (
            IMMUTABLE_CACHE if path.startswith(IMMUTABLE_PREFIX) else HTML_CACHE
        )
        return resp

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
    resp = send_from_directory(STATIC_DIR, "index.html")
    resp.headers["Cache-Control"] = HTML_CACHE
    return resp


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
