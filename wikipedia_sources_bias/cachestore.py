"""Pluggable persistence for the analyzer's lookup caches.

The CLI keeps the historical behaviour: one JSON file per namespace, next to
the repo. The Toolforge web app installs a MariaDB-backed store instead,
because a container's filesystem is wiped on every restart and is not shared
between worker replicas -- which meant every analysis re-hit Crossref, MBFC,
Wikidata and archive.org from scratch, for no reason and against their rate
limits.

The analyzer talks only to this interface, so it never imports a database
driver. The web app calls `set_store()` at startup; nothing else changes.

Namespaces are the old filenames minus ".json" ("page_cache", "mbfc_cache",
...), so a FileCacheStore reads and writes exactly the files that already
exist on disk.
"""
from __future__ import annotations

import json
import os
import threading
from typing import Any


class CacheStore:
    """A namespaced key/value store holding JSON-serialisable values."""

    def load_all(self, namespace: str) -> dict[str, Any]:
        raise NotImplementedError

    def get(self, namespace: str, key: str) -> Any | None:
        raise NotImplementedError

    def put(self, namespace: str, key: str, value: Any) -> None:
        raise NotImplementedError


class FileCacheStore(CacheStore):
    """One JSON file per namespace. The CLI default.

    Namespaces are held in memory after first read. The previous code called
    `_load_page_cache()` on every analysis, re-parsing a ~19MB file each time.
    """

    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self._data: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def _path(self, namespace: str) -> str:
        return os.path.join(self.base_dir, f"{namespace}.json")

    def _ns(self, namespace: str) -> dict[str, Any]:
        if namespace not in self._data:
            loaded: dict[str, Any] = {}
            path = self._path(namespace)
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                except Exception:
                    loaded = {}
            self._data[namespace] = loaded
        return self._data[namespace]

    def load_all(self, namespace):
        with self._lock:
            return dict(self._ns(namespace))

    def get(self, namespace, key):
        with self._lock:
            return self._ns(namespace).get(key)

    def put(self, namespace, key, value):
        with self._lock:
            ns = self._ns(namespace)
            ns[key] = value
            try:
                with open(self._path(namespace), "w", encoding="utf-8") as f:
                    json.dump(ns, f, indent=2, ensure_ascii=False)
            except Exception:
                # Caching is best-effort; a read-only checkout must not break
                # an analysis.
                pass


class MemoryCacheStore(CacheStore):
    """Non-persistent store, for tests and read-only environments."""

    def __init__(self):
        self._data: dict[str, dict[str, Any]] = {}

    def load_all(self, namespace):
        return dict(self._data.get(namespace, {}))

    def get(self, namespace, key):
        return self._data.get(namespace, {}).get(key)

    def put(self, namespace, key, value):
        self._data.setdefault(namespace, {})[key] = value


_store: CacheStore | None = None
_store_lock = threading.Lock()

# Historically the caches sat one level above the package (repo root when
# running from a checkout).
DEFAULT_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_store() -> CacheStore:
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = FileCacheStore(DEFAULT_BASE_DIR)
    return _store


def set_store(store: CacheStore | None) -> None:
    """Install a backend. Pass None to fall back to the file store."""
    global _store
    with _store_lock:
        _store = store
