"""In-memory cache for image matching results.

Stores match results from Step 3 so Step 4 can reuse them without re-running
image matching. Entries expire after a short TTL.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
import pickle
import threading
import uuid

from app.core.config import settings


_CACHE_TTL_SECONDS = 3600
_MAX_CACHE_ITEMS = 16
_LOCK = threading.Lock()
_CACHE: dict[str, "CachedMatch"] = {}


@dataclass(frozen=True)
class CachedMatch:
    """Cached match result with metadata for validation."""

    match: Any
    metadata: dict[str, Any]
    created_at: datetime


def store_match(match: Any, metadata: dict[str, Any]) -> str:
    """Store match result and return cache id."""
    match_id = uuid.uuid4().hex
    now = datetime.now(UTC)
    with _LOCK:
        _CACHE[match_id] = CachedMatch(match=match, metadata=metadata, created_at=now)
        removed = _cleanup_locked(now)
        _persist_match(match_id, match, metadata, now)
        for removed_id in removed:
            _delete_cache_file(removed_id)
    return match_id


def get_match(match_id: str) -> CachedMatch | None:
    """Get cached match by id (returns None if missing/expired)."""
    if not match_id:
        return None
    now = datetime.now(UTC)
    with _LOCK:
        entry = _CACHE.get(match_id)
        if entry is None:
            entry = _load_match(match_id)
            if entry is None:
                return None
            _CACHE[match_id] = entry
        if (now - entry.created_at).total_seconds() > _CACHE_TTL_SECONDS:
            _CACHE.pop(match_id, None)
            _delete_cache_file(match_id)
            return None
        return entry


def _cleanup_locked(now: datetime) -> list[str]:
    """Cleanup expired entries and evict oldest if cache is too large."""
    expired: list[str] = []
    for key, entry in _CACHE.items():
        if (now - entry.created_at).total_seconds() > _CACHE_TTL_SECONDS:
            expired.append(key)
    for key in expired:
        _CACHE.pop(key, None)

    if len(_CACHE) <= _MAX_CACHE_ITEMS:
        return expired

    # Evict oldest entries
    items = sorted(_CACHE.items(), key=lambda kv: kv[1].created_at)
    evicted: list[str] = []
    for key, _ in items[: len(_CACHE) - _MAX_CACHE_ITEMS]:
        _CACHE.pop(key, None)
        evicted.append(key)

    return expired + evicted


def _ensure_cache_dir() -> Path:
    cache_dir = settings.temp_dir / "match_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _cache_path(match_id: str) -> Path:
    return _ensure_cache_dir() / f"{match_id}.pkl"


def _persist_match(match_id: str, match: Any, metadata: dict[str, Any], created_at: datetime) -> None:
    payload = {
        "match": match,
        "metadata": metadata,
        "created_at": created_at.isoformat(),
    }
    try:
        with _cache_path(match_id).open("wb") as f:
            pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
    except Exception:
        # Best-effort persistence; keep in-memory cache even if disk write fails
        pass


def _load_match(match_id: str) -> CachedMatch | None:
    path = _cache_path(match_id)
    if not path.exists():
        return None
    try:
        with path.open("rb") as f:
            payload = pickle.load(f)
    except Exception:
        return None

    created_raw = payload.get("created_at")
    try:
        created_at = (
            datetime.fromisoformat(created_raw)
            if isinstance(created_raw, str)
            else datetime.now(UTC)
        )
    except Exception:
        created_at = datetime.now(UTC)

    return CachedMatch(
        match=payload.get("match"),
        metadata=payload.get("metadata", {}),
        created_at=created_at,
    )


def _delete_cache_file(match_id: str) -> None:
    try:
        _cache_path(match_id).unlink(missing_ok=True)
    except Exception:
        pass
