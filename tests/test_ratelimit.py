"""The limiter is what makes raising concurrency safe."""
import threading
import time

from wikipedia_sources_bias import ratelimit


def setup_function():
    ratelimit.reset()


def test_same_host_requests_are_spaced():
    ratelimit.MIN_INTERVAL_BY_HOST["ratetest.example"] = 0.05
    start = time.monotonic()
    for _ in range(4):
        ratelimit.wait("https://ratetest.example/a")
    elapsed = time.monotonic() - start
    # First call is free, the next three each wait one interval.
    assert elapsed >= 0.05 * 3 * 0.9, elapsed


def test_different_hosts_do_not_block_each_other():
    ratelimit.MIN_INTERVAL_BY_HOST["slowhost.example"] = 0.3
    ratelimit.wait("https://slowhost.example/a")
    start = time.monotonic()
    ratelimit.wait("https://otherhost.example/a")
    assert time.monotonic() - start < 0.1


def test_concurrent_threads_share_one_host_budget():
    """Threads must not each get their own allowance."""
    ratelimit.MIN_INTERVAL_BY_HOST["shared.example"] = 0.05
    start = time.monotonic()
    threads = [
        threading.Thread(target=ratelimit.wait, args=("https://shared.example/x",))
        for _ in range(5)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert time.monotonic() - start >= 0.05 * 4 * 0.9


def test_429_penalises_every_caller_of_that_host():
    class Resp:
        status_code = 429
        headers = {"Retry-After": "1"}

    ratelimit.note_response("https://penalised.example/x", Resp())
    start = time.monotonic()
    ratelimit.wait("https://penalised.example/other")
    assert time.monotonic() - start >= 0.9


def test_ok_responses_do_not_penalise():
    class Resp:
        status_code = 200
        headers = {}

    ratelimit.note_response("https://fine.example/x", Resp())
    start = time.monotonic()
    ratelimit.wait("https://fine.example/y")
    assert time.monotonic() - start < 0.1
