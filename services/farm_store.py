"""
farm_store.py - tiny persistence layer shared by the Farm Waste Market and River Watch.

Writes go to Supabase when it is configured and always to a local JSON file as well, so the app
keeps working offline and nothing is lost if the cloud is unreachable. Reads prefer Supabase and
fall back to the local file.

Tables (see docs/supabase_schema_v2.sql): scrap_listings, scrap_buyers, scrap_inquiries, river_incidents,
buyer_demands, demand_offers.
Every row has a text `id` (uuid) and `created_at` (ISO timestamp) that are filled in here.
"""

import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

try:
    from services import supabase_client as _supa
except Exception:  # pragma: no cover - supabase is optional
    _supa = None

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_LOCAL_DIR = os.path.join(_ROOT, "scratch")
_LOCK = threading.Lock()
_CACHE: Dict[Any, Any] = {}
_CACHE_TTL_S = 60.0   # Streamlit re-runs the whole script on every click; without this each rerun hits the cloud
_TABLES = {"scrap_listings", "scrap_buyers", "scrap_inquiries", "river_incidents", "buyer_demands", "demand_offers"}


def _path(table: str) -> str:
    return os.path.join(_LOCAL_DIR, f"{table}.json")


def _check(table: str) -> None:
    if table not in _TABLES:
        raise ValueError(f"unknown table: {table}")


def _read_local(table: str) -> List[Dict[str, Any]]:
    try:
        with open(_path(table), "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _write_local(table: str, rows: List[Dict[str, Any]]) -> None:
    os.makedirs(_LOCAL_DIR, exist_ok=True)
    tmp = _path(table) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False)
    os.replace(tmp, _path(table))


def _client():
    if _supa is None:
        return None
    try:
        return _supa.get_supabase_client()
    except Exception:
        return None


def backend() -> str:
    """'supabase' when the cloud client is available, else 'local'."""
    return "supabase" if _client() is not None else "local"


def _invalidate(table: str, keep_full: bool = False) -> None:
    for k in [k for k in _CACHE if k[0] == table and not (keep_full and k[1] == ())]:
        _CACHE.pop(k, None)


def _quiet(fn) -> None:
    try:
        fn()
    except Exception:
        pass


_REFRESHING: set = set()


def _fetch(table: str, equals: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: Optional[List[Dict[str, Any]]] = None
    client = _client()
    if client is not None:
        try:
            query = client.table(table).select("*")
            for k, v in equals.items():
                query = query.eq(k, v)
            rows = query.order("created_at", desc=True).limit(500).execute().data
        except Exception:
            rows = None
    if rows is None:
        rows = [r for r in _read_local(table) if all(r.get(k) == v for k, v in equals.items())]
    return rows


def prefetch(tables: Iterable[str]) -> None:
    """Warm the read cache in the background (a cheap no-op once the tables are cached)."""
    todo = [t for t in tables if (t, ()) not in _CACHE and (t, ()) not in _REFRESHING]
    if not todo:
        return
    _REFRESHING.update((t, ()) for t in todo)

    def work():
        for t in todo:
            try:
                _quiet(lambda t=t: _CACHE.__setitem__((t, ()), (time.time(), _fetch(t, {}))))
            finally:
                _REFRESHING.discard((t, ()))
    threading.Thread(target=work, daemon=True).start()


def insert(table: str, row: Dict[str, Any]) -> Dict[str, Any]:
    _check(table)
    _invalidate(table, keep_full=True)
    row = dict(row)
    row.setdefault("id", uuid.uuid4().hex)
    row.setdefault("created_at", datetime.now(timezone.utc).isoformat())
    with _LOCK:
        rows = _read_local(table)
        rows.insert(0, row)
        _write_local(table, rows)
        full = _CACHE.get((table, ()))
        if full:                                   # show the new row at once, without a cloud round trip
            _CACHE[(table, ())] = (full[0], [row] + list(full[1]))
    client = _client()
    if client is not None:
        _quiet(lambda: client.table(table).insert(row).execute())   # local copy is saved; cloud is best effort
    return row


def select(table: str, **equals: Any) -> List[Dict[str, Any]]:
    """All rows (newest first) whose columns equal the given values (cached for a few seconds)."""
    _check(table)
    ckey = (table, tuple(sorted(equals.items())))
    hit = _CACHE.get(ckey)
    if hit:
        if time.time() - hit[0] >= _CACHE_TTL_S and ckey not in _REFRESHING:
            # stale: answer now from the cached copy and refresh in the background
            _REFRESHING.add(ckey)

            def refresh(ckey=ckey):
                try:
                    _CACHE[ckey] = (time.time(), _fetch(table, equals))
                finally:
                    _REFRESHING.discard(ckey)
            threading.Thread(target=lambda: _quiet(refresh), daemon=True).start()
        return list(hit[1])
    rows = _fetch(table, equals)
    _CACHE[ckey] = (time.time(), list(rows))
    return rows


def update(table: str, row_id: str, patch: Dict[str, Any]) -> bool:
    _check(table)
    # patch cached copies in place instead of dropping them, so the next page run needs no cloud read
    for k, (ts, cached) in list(_CACHE.items()):
        if k[0] == table:
            _CACHE[k] = (ts, [({**r, **patch} if r.get("id") == row_id else r) for r in cached])
    ok = False
    with _LOCK:
        rows = _read_local(table)
        for r in rows:
            if r.get("id") == row_id:
                r.update(patch)
                ok = True
        if ok:
            _write_local(table, rows)
    client = _client()
    if client is not None:
        try:
            client.table(table).update(patch).eq("id", row_id).execute()
            ok = True
        except Exception:
            pass
    return ok


def delete(table: str, **equals: Any) -> int:
    """Deletes rows whose columns equal the given values (locally and in the cloud). Returns how many local rows went."""
    _check(table)
    _invalidate(table)
    with _LOCK:
        rows = _read_local(table)
        keep = [r for r in rows if not all(r.get(k) == v for k, v in equals.items())]
        removed = len(rows) - len(keep)
        _write_local(table, keep)
    client = _client()
    if client is not None and equals:
        try:
            query = client.table(table).delete()
            for k, v in equals.items():
                query = query.eq(k, v)
            query.execute()
        except Exception:
            pass
    return removed
