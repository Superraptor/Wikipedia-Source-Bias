"""A worker was OOMKilled (exit 137) with no record of its memory use.

The cause was `response.text` on a multi-megabyte PDF, now capped, but the
absence of any measurement meant the only evidence was a notification email.
"""
import worker


def test_rss_is_reported_as_a_number():
    rss = worker._rss_mb()
    # None on platforms without /proc (macOS dev machines); a plausible figure
    # everywhere else.
    assert rss is None or (0 < rss < 100_000)


def test_the_warning_threshold_leaves_real_headroom():
    """It must fire well before the 1Gi container limit, not at it."""
    assert worker.RSS_WARN_MB < 1024
    assert worker.RSS_WARN_MB >= 256
