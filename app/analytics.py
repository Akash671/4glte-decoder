"""
Lightweight usage analytics, shared by the FastAPI service and the
Streamlit GUI.

Backed by SQLite so both processes can read/write the same counters without
extra infrastructure. Each call opens and closes its own connection --
cheap enough at this traffic scale, and avoids cross-thread/cross-process
sqlite3 connection-sharing issues (Streamlit and Uvicorn both run
multi-threaded).

IMPORTANT -- persistence caveat:
Streamlit Community Cloud (and most free container hosts) use an EPHEMERAL
filesystem: the DB file lives only as long as the current container
instance. It survives page reloads and reruns within a session, but resets
on every app restart/redeploy/sleep-wake cycle. That's fine for a portfolio
demo, but for numbers that need to survive redeploys, swap this module's
storage for a hosted DB (e.g. Supabase's free Postgres tier) behind the same
record_event()/get_stats() interface -- nothing else in the app needs to
change.

For Docker/self-hosted deployments, persistence is easy: mount a volume at
the DB path (see docker-compose.yml) and it survives container restarts.
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

DB_PATH = os.getenv("ANALYTICS_DB_PATH", os.path.join(os.path.dirname(__file__), "..", "analytics.db"))


@contextmanager
def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=5)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create the events table if it doesn't exist yet. Safe to call repeatedly."""
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                event_type TEXT NOT NULL,
                layer TEXT,
                success INTEGER
            )
            """
        )


def record_event(event_type: str, layer: str | None = None, success: bool | None = None) -> None:
    """
    Record a single event.

    event_type: e.g. "page_view", "gui_decode", "api_decode"
    layer:      "RRC" / "NAS", when applicable
    success:    True/False for decode events, None for events with no
                pass/fail concept (e.g. page_view)
    """
    init_db()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO events (ts, event_type, layer, success) VALUES (?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(),
                event_type,
                layer,
                None if success is None else int(success),
            ),
        )


def get_stats() -> dict:
    """Return aggregated counters for display in the GUI/API."""
    init_db()
    with _connect() as conn:
        conn.row_factory = sqlite3.Row

        total_views = conn.execute(
            "SELECT COUNT(*) AS c FROM events WHERE event_type = 'page_view'"
        ).fetchone()["c"]

        decode_rows = conn.execute(
            "SELECT event_type, layer, success, COUNT(*) AS c "
            "FROM events WHERE event_type IN ('gui_decode', 'api_decode') "
            "GROUP BY event_type, layer, success"
        ).fetchall()

        total_decodes = 0
        by_layer: dict[str, int] = {}
        success_count = 0
        error_count = 0
        by_source: dict[str, int] = {"gui_decode": 0, "api_decode": 0}

        for row in decode_rows:
            total_decodes += row["c"]
            by_source[row["event_type"]] = by_source.get(row["event_type"], 0) + row["c"]
            if row["layer"]:
                by_layer[row["layer"]] = by_layer.get(row["layer"], 0) + row["c"]
            if row["success"] == 1:
                success_count += row["c"]
            elif row["success"] == 0:
                error_count += row["c"]

        last_event = conn.execute(
            "SELECT ts FROM events ORDER BY id DESC LIMIT 1"
        ).fetchone()

        return {
            "total_views": total_views,
            "total_decodes": total_decodes,
            "decodes_by_layer": by_layer,
            "decodes_by_source": by_source,
            "success_count": success_count,
            "error_count": error_count,
            "success_rate": round(success_count / total_decodes, 3) if total_decodes else None,
            "last_event_at": last_event["ts"] if last_event else None,
        }


def reset_db() -> None:
    """Wipe all recorded events. Used by tests; not exposed via any endpoint."""
    init_db()
    with _connect() as conn:
        conn.execute("DELETE FROM events")
