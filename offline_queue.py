"""
offline_queue.py — The Rebar Company
Queues clock-in/out records when offline and syncs when back online.
"""

import sqlite3
import os
import json
from datetime import datetime
import database as db

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
QUEUE_PATH = os.path.join(BASE_DIR, "database", "offline_queue.db")


def get_queue_connection():
    conn = sqlite3.connect(QUEUE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS queue (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            action      TEXT    NOT NULL,
            method      TEXT    NOT NULL DEFAULT 'manual',
            location    TEXT,
            queued_at   TEXT    NOT NULL,
            synced      INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()
    return conn


def is_online() -> bool:
    """Check if we can reach the local Flask server or internet."""
    try:
        import urllib.request
        urllib.request.urlopen("http://127.0.0.1:5000/login", timeout=2)
        return True
    except Exception:
        return False


def queue_clock_in(employee_id: int, method="manual", location=None):
    """Add a clock-in to the offline queue."""
    conn = get_queue_connection()
    try:
        conn.execute(
            """INSERT INTO queue (employee_id, action, method, location, queued_at)
               VALUES (?, 'clock_in', ?, ?, ?)""",
            (employee_id, method, location, db.now_local())
        )
        conn.commit()
        print(f"[OFFLINE] Clock-in queued for employee {employee_id}")
    finally:
        conn.close()


def queue_clock_out(employee_id: int):
    """Add a clock-out to the offline queue."""
    conn = get_queue_connection()
    try:
        conn.execute(
            """INSERT INTO queue (employee_id, action, method, queued_at)
               VALUES (?, 'clock_out', 'manual', ?)""",
            (employee_id, db.now_local())
        )
        conn.commit()
        print(f"[OFFLINE] Clock-out queued for employee {employee_id}")
    finally:
        conn.close()


def get_pending_count() -> int:
    """Return number of unsynced queue items."""
    conn = get_queue_connection()
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM queue WHERE synced = 0"
        ).fetchone()[0]
    finally:
        conn.close()


def sync_queue() -> dict:
    """
    Process all unsynced queue items.
    Returns a summary dict with success/fail counts.
    """
    conn = get_queue_connection()
    try:
        pending = conn.execute(
            "SELECT * FROM queue WHERE synced = 0 ORDER BY queued_at"
        ).fetchall()
    finally:
        conn.close()

    success = 0
    failed  = 0
    errors  = []

    for item in pending:
        try:
            if item["action"] == "clock_in":
                db.clock_in(
                    item["employee_id"],
                    method=item["method"] + "_offline",
                    location=item["location"]
                )
            elif item["action"] == "clock_out":
                db.clock_out(item["employee_id"])

            # Mark as synced
            qconn = get_queue_connection()
            qconn.execute("UPDATE queue SET synced = 1 WHERE id = ?", (item["id"],))
            qconn.commit()
            qconn.close()
            success += 1

        except Exception as e:
            failed += 1
            errors.append(f"Item {item['id']}: {str(e)}")

    print(f"[OFFLINE] Sync complete — {success} success, {failed} failed")
    return {"success": success, "failed": failed, "errors": errors}


def get_queue_items():
    """Return all pending queue items for display."""
    conn = get_queue_connection()
    try:
        return conn.execute(
            """SELECT q.*, e.full_name, e.employee_code
               FROM queue q
               LEFT JOIN main.employees e ON e.id = q.employee_id
               WHERE q.synced = 0
               ORDER BY q.queued_at""",
        ).fetchall()
    except Exception:
        # fallback without join
        conn2 = get_queue_connection()
        return conn2.execute(
            "SELECT * FROM queue WHERE synced = 0 ORDER BY queued_at"
        ).fetchall()
    finally:
        conn.close()