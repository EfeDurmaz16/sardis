"""Test thread-safety of ReplayCache with concurrent access."""
import threading
import time
from sardis_protocol.storage import ReplayCache


def test_replay_cache_concurrent_access():
    """Test that ReplayCache is thread-safe with 100 concurrent threads."""
    cache = ReplayCache()

    # Track results from all threads
    results = []
    errors = []

    def worker(thread_id: int):
        """Worker function that tries to store mandates."""
        try:
            mandate_id = f"mandate-{thread_id}"
            expires_at = int(time.time()) + 3600

            # Each thread should successfully store its own mandate_id
            result = cache.check_and_store(mandate_id, expires_at)
            results.append((thread_id, mandate_id, result))
        except Exception as e:
            errors.append((thread_id, str(e)))

    # Create 100 threads
    threads = []
    for i in range(100):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)

    # Start all threads
    for t in threads:
        t.start()

    # Wait for all to complete
    for t in threads:
        t.join()

    # Verify no errors occurred
    assert len(errors) == 0, f"Thread-safety errors occurred: {errors}"

    # Verify all 100 mandates were stored successfully
    assert len(results) == 100, f"Expected 100 results, got {len(results)}"

    # All should have returned True (first time storing)
    all_true = all(result[2] for result in results)
    assert all_true, "All first-time stores should return True"

    # Verify all mandate_ids are in cache
    stats = cache.stats()
    assert stats["total_entries"] == 100, f"Expected 100 entries, got {stats['total_entries']}"


def test_replay_cache_concurrent_duplicate():
    """Test that ReplayCache correctly rejects duplicates under concurrent access."""
    cache = ReplayCache()

    # Use the SAME mandate_id for all threads
    shared_mandate_id = "shared-mandate"
    expires_at = int(time.time()) + 3600

    results = []
    errors = []

    def worker(thread_id: int):
        """Worker that tries to store the same mandate_id."""
        try:
            result = cache.check_and_store(shared_mandate_id, expires_at)
            results.append((thread_id, result))
        except Exception as e:
            errors.append((thread_id, str(e)))

    # Create 100 threads all trying to store the same mandate_id
    threads = []
    for i in range(100):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)

    # Start all threads
    for t in threads:
        t.start()

    # Wait for all to complete
    for t in threads:
        t.join()

    # Verify no errors
    assert len(errors) == 0, f"Thread-safety errors: {errors}"

    # Exactly ONE thread should have returned True, rest should be False
    true_count = sum(1 for _, result in results if result)
    false_count = sum(1 for _, result in results if not result)

    assert true_count == 1, f"Expected exactly 1 True result, got {true_count}"
    assert false_count == 99, f"Expected 99 False results, got {false_count}"

    # Cache should have exactly 1 entry
    stats = cache.stats()
    assert stats["total_entries"] == 1, f"Expected 1 entry, got {stats['total_entries']}"


def test_replay_cache_concurrent_cleanup():
    """Test that cleanup is thread-safe when called concurrently."""
    cache = ReplayCache()

    # Add some mandates with past expiration
    now = int(time.time())
    for i in range(50):
        cache._seen[f"expired-{i}"] = now - 100  # Already expired
        cache._seen[f"active-{i}"] = now + 3600   # Still active

    cleanup_results = []
    errors = []

    def cleanup_worker(thread_id: int):
        """Worker that calls cleanup."""
        try:
            removed = cache.cleanup(now)
            cleanup_results.append((thread_id, removed))
        except Exception as e:
            errors.append((thread_id, str(e)))

    # Create 10 threads all calling cleanup
    threads = []
    for i in range(10):
        t = threading.Thread(target=cleanup_worker, args=(i,))
        threads.append(t)

    # Start all threads
    for t in threads:
        t.start()

    # Wait for all to complete
    for t in threads:
        t.join()

    # Verify no errors
    assert len(errors) == 0, f"Cleanup errors: {errors}"

    # After cleanup, only active entries should remain
    stats = cache.stats()
    assert stats["total_entries"] == 50, f"Expected 50 active entries, got {stats['total_entries']}"
    assert stats["expired_entries"] == 0, "No expired entries should remain"


def test_replay_cache_stats_thread_safe():
    """Test that stats() is thread-safe."""
    cache = ReplayCache()

    # Pre-populate cache
    now = int(time.time())
    for i in range(100):
        cache._seen[f"mandate-{i}"] = now + 3600

    stats_results = []
    errors = []

    def stats_worker(thread_id: int):
        """Worker that reads stats."""
        try:
            stats = cache.stats()
            stats_results.append((thread_id, stats))
        except Exception as e:
            errors.append((thread_id, str(e)))

    # Create 50 threads reading stats
    threads = []
    for i in range(50):
        t = threading.Thread(target=stats_worker, args=(i,))
        threads.append(t)

    # Start all threads
    for t in threads:
        t.start()

    # Wait for all to complete
    for t in threads:
        t.join()

    # Verify no errors
    assert len(errors) == 0, f"Stats errors: {errors}"

    # All stats should show 100 total entries
    for thread_id, stats in stats_results:
        assert stats["total_entries"] == 100, f"Thread {thread_id} saw {stats['total_entries']} entries"
