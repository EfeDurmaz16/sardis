"""Utility classes for Sardis core.

Provides common data structures and helpers used across packages.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Generic, Iterator, Optional, TypeVar

K = TypeVar("K")
V = TypeVar("V")


@dataclass
class TTLEntry(Generic[V]):
    """Entry in TTLDict with expiration tracking."""
    
    value: V
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    
    def is_expired(self, ttl_seconds: float) -> bool:
        """Check if entry has expired based on creation time."""
        return (time.time() - self.created_at) > ttl_seconds
    
    def touch(self) -> None:
        """Update last accessed time."""
        self.last_accessed = time.time()


class TTLDict(Generic[K, V]):
    """
    Thread-safe dictionary with TTL expiration and max size limits.
    
    Prevents memory leaks in long-running processes by automatically
    expiring old entries and enforcing maximum size limits.
    
    Features:
    - Configurable TTL (time-to-live) for entries
    - Maximum size limit with LRU-like eviction
    - Automatic cleanup on access (lazy expiration)
    - Optional periodic cleanup callback
    - Thread-safe operations
    
    Usage:
        # Create with 1-hour TTL and max 1000 items
        cache = TTLDict[str, Wallet](ttl_seconds=3600, max_items=1000)
        
        # Use like a regular dict
        cache["wallet_123"] = wallet
        wallet = cache.get("wallet_123")
        
        # Check if key exists (also cleans expired)
        if "wallet_123" in cache:
            ...
    
    Args:
        ttl_seconds: Time-to-live for entries in seconds. Default 86400 (24 hours).
        max_items: Maximum number of items to store. Default 10000.
        cleanup_interval: Minimum seconds between full cleanup runs. Default 300 (5 min).
    """
    
    def __init__(
        self,
        ttl_seconds: float = 86400,  # 24 hours
        max_items: int = 10000,
        cleanup_interval: float = 300,  # 5 minutes
    ) -> None:
        self._data: Dict[K, TTLEntry[V]] = {}
        self._ttl_seconds = ttl_seconds
        self._max_items = max_items
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()
        self._lock = threading.RLock()
    
    @property
    def ttl_seconds(self) -> float:
        """Get the TTL in seconds."""
        return self._ttl_seconds
    
    @property
    def max_items(self) -> int:
        """Get the maximum number of items."""
        return self._max_items
    
    def __len__(self) -> int:
        """Return number of items (including possibly expired)."""
        with self._lock:
            return len(self._data)
    
    def __contains__(self, key: K) -> bool:
        """Check if key exists and is not expired."""
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return False
            if entry.is_expired(self._ttl_seconds):
                del self._data[key]
                return False
            return True
    
    def __setitem__(self, key: K, value: V) -> None:
        """Set a value, enforcing max size."""
        with self._lock:
            self._maybe_cleanup()
            
            # If at max capacity and key is new, evict oldest
            if key not in self._data and len(self._data) >= self._max_items:
                self._evict_oldest()
            
            self._data[key] = TTLEntry(value=value)
    
    def __getitem__(self, key: K) -> V:
        """Get a value, raising KeyError if not found or expired."""
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                raise KeyError(key)
            if entry.is_expired(self._ttl_seconds):
                del self._data[key]
                raise KeyError(key)
            entry.touch()
            return entry.value
    
    def __delitem__(self, key: K) -> None:
        """Delete a key."""
        with self._lock:
            del self._data[key]
    
    def get(self, key: K, default: Optional[V] = None) -> Optional[V]:
        """Get a value or return default if not found/expired."""
        try:
            return self[key]
        except KeyError:
            return default
    
    def set(self, key: K, value: V) -> None:
        """Set a value (alias for __setitem__)."""
        self[key] = value
    
    def pop(self, key: K, default: Optional[V] = None) -> Optional[V]:
        """Remove and return a value."""
        with self._lock:
            entry = self._data.pop(key, None)
            if entry is None:
                return default
            if entry.is_expired(self._ttl_seconds):
                return default
            return entry.value
    
    def keys(self) -> Iterator[K]:
        """Iterate over non-expired keys."""
        with self._lock:
            now = time.time()
            expired = []
            for key, entry in self._data.items():
                if entry.is_expired(self._ttl_seconds):
                    expired.append(key)
                else:
                    yield key
            # Clean up expired entries
            for key in expired:
                del self._data[key]
    
    def values(self) -> Iterator[V]:
        """Iterate over non-expired values."""
        with self._lock:
            now = time.time()
            expired = []
            for key, entry in self._data.items():
                if entry.is_expired(self._ttl_seconds):
                    expired.append(key)
                else:
                    yield entry.value
            # Clean up expired entries
            for key in expired:
                del self._data[key]
    
    def items(self) -> Iterator[tuple[K, V]]:
        """Iterate over non-expired key-value pairs."""
        with self._lock:
            now = time.time()
            expired = []
            for key, entry in self._data.items():
                if entry.is_expired(self._ttl_seconds):
                    expired.append(key)
                else:
                    yield key, entry.value
            # Clean up expired entries
            for key in expired:
                del self._data[key]
    
    def clear(self) -> None:
        """Remove all items."""
        with self._lock:
            self._data.clear()
    
    def cleanup(self) -> int:
        """
        Remove all expired entries.
        
        Returns:
            Number of entries removed.
        """
        with self._lock:
            expired = [
                key for key, entry in self._data.items()
                if entry.is_expired(self._ttl_seconds)
            ]
            for key in expired:
                del self._data[key]
            self._last_cleanup = time.time()
            return len(expired)
    
    def _maybe_cleanup(self) -> None:
        """Run cleanup if interval has elapsed."""
        if (time.time() - self._last_cleanup) >= self._cleanup_interval:
            self.cleanup()
    
    def _evict_oldest(self) -> None:
        """Evict the oldest entry (by last access time)."""
        if not self._data:
            return
        
        oldest_key = min(
            self._data.keys(),
            key=lambda k: self._data[k].last_accessed,
        )
        del self._data[oldest_key]
    
    def stats(self) -> dict:
        """Return statistics about the cache."""
        with self._lock:
            now = time.time()
            expired_count = sum(
                1 for entry in self._data.values()
                if entry.is_expired(self._ttl_seconds)
            )
            return {
                "total_items": len(self._data),
                "expired_items": expired_count,
                "active_items": len(self._data) - expired_count,
                "max_items": self._max_items,
                "ttl_seconds": self._ttl_seconds,
                "last_cleanup": self._last_cleanup,
            }


class BoundedDict(Generic[K, V]):
    """
    Simple bounded dictionary without TTL.
    
    Useful when you only need size limits, not expiration.
    Evicts oldest entries when at capacity.
    """
    
    def __init__(self, max_items: int = 10000) -> None:
        self._data: Dict[K, V] = {}
        self._max_items = max_items
        self._lock = threading.RLock()
    
    def __len__(self) -> int:
        with self._lock:
            return len(self._data)
    
    def __contains__(self, key: K) -> bool:
        with self._lock:
            return key in self._data
    
    def __setitem__(self, key: K, value: V) -> None:
        with self._lock:
            if key not in self._data and len(self._data) >= self._max_items:
                # Remove first item (oldest in insertion order for Python 3.7+)
                first_key = next(iter(self._data))
                del self._data[first_key]
            self._data[key] = value
    
    def __getitem__(self, key: K) -> V:
        with self._lock:
            return self._data[key]
    
    def __delitem__(self, key: K) -> None:
        with self._lock:
            del self._data[key]
    
    def get(self, key: K, default: Optional[V] = None) -> Optional[V]:
        with self._lock:
            return self._data.get(key, default)
    
    def pop(self, key: K, default: Optional[V] = None) -> Optional[V]:
        with self._lock:
            return self._data.pop(key, default)
    
    def clear(self) -> None:
        with self._lock:
            self._data.clear()
    
    def keys(self) -> Iterator[K]:
        with self._lock:
            yield from list(self._data.keys())
    
    def values(self) -> Iterator[V]:
        with self._lock:
            yield from list(self._data.values())
    
    def items(self) -> Iterator[tuple[K, V]]:
        with self._lock:
            yield from list(self._data.items())
