"""Queue worker: drains pending analyses into the ToolsDB cache.

Runs as a Toolforge continuous job (see jobs.yaml). The web tier only enqueues
and reads; this is the only process that performs an analysis, which is what
keeps a multi-minute scrape out of an HTTP request.

    toolforge jobs run worker \
        --image tool-wikibias-analyzer/tool-wikibias-analyzer:latest \
        --command worker --continuous --mem 2Gi --cpu 1
"""
import signal
import sys
import time

import config
from cache import Cache
from runner import run_analysis, AnalysisUnavailable

IDLE_SLEEP_SECONDS = 10
STALE_SWEEP_EVERY = 60  # loop iterations between stale-row sweeps

_running = True


def _stop(signum, _frame):
    global _running
    _running = False
    print(f"Received signal {signum}, finishing current item then exiting.", flush=True)


def log(msg):
    print(msg, flush=True)


def main():
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    conn = config.connect()
    cache = Cache(conn)
    log(f"Worker started against {config.db_params()['database']}")

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
            recovered = cache.requeue_stale_running()
            if recovered:
                log(f"Requeued {recovered} stale running row(s)")
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
        started = time.monotonic()
        try:
            result = run_analysis(url)
        except Exception as e:
            log(f"  FAILED after {time.monotonic() - started:.1f}s: {e}")
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

    log("Worker stopped.")


if __name__ == "__main__":
    main()
