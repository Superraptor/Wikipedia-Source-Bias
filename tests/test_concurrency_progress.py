"""A slow source must not hide the progress of the ones that finished.

pool.map yields strictly in submission order, so an article whose FIRST source
hung reported no progress and checkpointed nothing for its entire run -- and
the stale sweep then requeued it every 10 minutes indefinitely.
"""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


def _drain(pending, work, report):
    """Mirrors analyze_page's collection strategy."""
    results, collected = {}, []
    next_index = pending[0][0]
    completed = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(work, i): i for i, _ in pending}
        for future in as_completed(futures):
            index = futures[future]
            results[index] = future.result()
            completed += 1
            report(completed)
            while next_index in results:
                collected.append(results.pop(next_index))
                next_index += 1
    return collected


def test_progress_advances_while_the_first_item_is_slow():
    pending = [(i, f"u{i}") for i in range(1, 5)]
    seen = []

    def work(i):
        if i == 1:
            time.sleep(0.4)      # the straggler
        return i

    _drain(pending, work, seen.append)
    # The three fast items reported before the slow one finished.
    assert seen[:3] == [1, 2, 3]
    assert max(seen) == 4


def test_results_are_still_collected_in_index_order():
    """Resumption relies on `sources` being ordered."""
    pending = [(i, f"u{i}") for i in range(1, 6)]

    def work(i):
        time.sleep(0.05 * (6 - i))   # finish in reverse order
        return i

    assert _drain(pending, work, lambda _n: None) == [1, 2, 3, 4, 5]


def test_a_failing_source_still_propagates():
    pending = [(1, "u1"), (2, "u2")]

    def work(i):
        if i == 2:
            raise RuntimeError("boom")
        return i

    try:
        _drain(pending, work, lambda _n: None)
    except RuntimeError as e:
        assert "boom" in str(e)
    else:
        raise AssertionError("the failure should have propagated")
