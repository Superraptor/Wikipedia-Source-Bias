"""Queue worker: drains pending analyses into the ToolsDB cache.

Runs as a Toolforge continuous job (see jobs.yaml). The web tier only enqueues
and reads; this is the only process that performs an analysis, which is what
keeps a multi-minute scrape out of an HTTP request.

    toolforge jobs run worker \
        --image tool-wikibias-analyzer/tool-wikibias-analyzer:latest \
        --command worker --continuous --mem 2Gi --cpu 1
"""
import os
import signal
import sys
import time

import config
from cache import Cache
from runner import run_analysis, AnalysisUnavailable

IDLE_SLEEP_SECONDS = 10
STALE_SWEEP_EVERY = 6  # loop iterations between stale-row sweeps (~1 min)

# How long a row may sit in 'running' before another worker may reclaim it.
# Kubernetes kills a pod ~30s after SIGTERM, so an analysis interrupted by a
# redeploy leaves its row claimed with nobody working on it. This used to be
# 30 minutes, which is how a redeploy left articles apparently "running" for
# half an hour.
STALE_MINUTES = 10

# Minimum gap between progress writes for one analysis.
PROGRESS_EVERY_SECONDS = 5

# Weight of the newest sample in the seconds-per-source estimate. Low enough to
# absorb one slow source, high enough to follow a real change in throughput.
EWMA_ALPHA = 0.3

_running = True
# The row this process currently holds, so a graceful shutdown can release it
# instead of leaving it claimed.
_current_url = None


def _stop(signum, _frame):
    global _running
    _running = False
    print(f"Received signal {signum}, releasing current item and exiting.", flush=True)


def log(msg):
    print(msg, flush=True)


def main():
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    conn = config.connect()
    cache = Cache(conn)
    log(f"Worker started against {config.db_params()['database']}")

    # Point the analyzer's lookup caches (MBFC, Wikidata, Crossref, nametrace,
    # page) at ToolsDB. Otherwise they land in the container filesystem, which
    # is wiped on restart and not shared with the other replica -- every
    # analysis would re-hit those APIs from scratch.
    if config.on_toolforge() or os.environ.get("USE_DB_CACHESTORE"):
        import db_cachestore

        db_cachestore.install(config.connect)
        log("Analyzer lookup caches -> ToolsDB (kv_cache)")

    # Fail fast and loudly if the analyzer is unavailable, rather than
    # discovering it one job at a time.
    try:
        from runner import _load_analyzer

        _load_analyzer()
    except AnalysisUnavailable as e:
        log(f"FATAL: {e}")
        sys.exit(1)

    ticks = 0
    while _running:
        if ticks % STALE_SWEEP_EVERY == 0:
            recovered, failed = cache.requeue_stale_running(STALE_MINUTES)
            if recovered:
                log(f"Requeued {recovered} stale running row(s)")
            if failed:
                log(f"Marked {failed} exhausted row(s) as failed")
        ticks += 1

        try:
            url = cache.claim_next()
        except Exception as e:
            log(f"Queue read failed, retrying: {e}")
            time.sleep(IDLE_SLEEP_SECONDS)
            continue

        if url is None:
            time.sleep(IDLE_SLEEP_SECONDS)
            continue

        log(f"Analyzing {url}")
        globals()["_current_url"] = url
        started = time.monotonic()

        # Throttled: an 880-source article would otherwise issue 880 UPDATEs.
        last_report = [0.0]
        # Exponentially weighted mean seconds-per-source. A cumulative average
        # made the ETA drift upward for the whole run whenever later sources
        # were slower than earlier ones; an EWMA tracks the current rate, so
        # the estimate converges instead of climbing.
        ewma = [None]
        last_tick = [started]

        def report(stage, done, total):
            now = time.monotonic()

            if done > 0:
                gap = now - last_tick[0]
                last_tick[0] = now
                if gap > 0:
                    ewma[0] = gap if ewma[0] is None else (EWMA_ALPHA * gap
                                                           + (1 - EWMA_ALPHA) * ewma[0])

            if now - last_report[0] < PROGRESS_EVERY_SECONDS and done != total:
                return
            last_report[0] = now

            eta = None
            if ewma[0] and total and done < total:
                eta = int(ewma[0] * (total - done))
            try:
                cache.set_progress(url, stage, done, total, eta)
            except Exception:
                pass

        try:
            result = run_analysis(url, progress_cb=report)
        except Exception as e:
            log(f"  FAILED after {time.monotonic() - started:.1f}s: {e}")
            # Cleared here too: this branch `continue`s past the finally
            # below, and a stale value would make the shutdown handler
            # re-queue a row we just marked failed.
            globals()["_current_url"] = None
            try:
                cache.mark_error(url, e)
            except Exception as inner:
                log(f"  could not record failure: {inner}")
            continue

        try:
            cache.set(url, result)
            log(
                f"  done in {time.monotonic() - started:.1f}s, "
                f"{result.get('source_count')} sources"
            )
        except Exception as e:
            log(f"  analysis succeeded but caching failed: {e}")
        finally:
            globals()["_current_url"] = None

    # Hand back anything still claimed, so a redeploy does not strand a row in
    # 'running' until the stale sweep notices.
    if _current_url:
        try:
            cache.release(_current_url)
            log(f"Released {_current_url} back to the queue.")
        except Exception as e:
            log(f"Could not release {_current_url}: {e}")

    log("Worker stopped.")


if __name__ == "__main__":
    main()
