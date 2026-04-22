"""
database.py — The Rebar Company
Handles all SQLite database creation, schema migrations, and helper utilities.
"""

import sqlite3
import os
import hashlib
import secrets
from datetime import datetime
import pytz

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "database", "rebar.db")
TIMEZONE = pytz.timezone("Australia/Melbourne")


def now_local() -> str:
    """Return current time in Australian Eastern time as ISO string."""
    return datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


# ─────────────────────────────────────────────
# SCHEMA
# ─────────────────────────────────────────────

SCHEMA = """

CREATE TABLE IF NOT EXISTS employees (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_code   TEXT    NOT NULL UNIQUE,
    full_name       TEXT    NOT NULL,
    email           TEXT    UNIQUE,
    phone           TEXT,
    role            TEXT    NOT NULL DEFAULT 'employee',
    department      TEXT,
    pin_hash        TEXT,
    password_hash   TEXT,
    face_enrolled   INTEGER NOT NULL DEFAULT 0,
    wifi_mac        TEXT,
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS face_encodings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id     INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    encoding_blob   BLOB    NOT NULL,
    label           TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS clock_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id     INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    clock_in        TEXT    NOT NULL,
    clock_out       TEXT,
    method          TEXT    NOT NULL DEFAULT 'manual',
    location        TEXT,
    notes           TEXT,
    total_minutes   INTEGER
);

CREATE INDEX IF NOT EXISTS idx_clock_employee ON clock_records(employee_id);
CREATE INDEX IF NOT EXISTS idx_clock_in       ON clock_records(clock_in);

CREATE TABLE IF NOT EXISTS leave_requests (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id     INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    leave_type      TEXT    NOT NULL,
    start_date      TEXT    NOT NULL,
    end_date        TEXT    NOT NULL,
    days_count      REAL,
    status          TEXT    NOT NULL DEFAULT 'pending',
    approved_by     INTEGER REFERENCES employees(id),
    reason          TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS documents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT    NOT NULL,
    category        TEXT    NOT NULL DEFAULT 'general',
    file_path       TEXT    NOT NULL,
    file_name       TEXT    NOT NULL,
    file_size_kb    INTEGER,
    uploaded_by     INTEGER REFERENCES employees(id),
    is_public       INTEGER NOT NULL DEFAULT 0,
    expiry_date     TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS document_access (
    document_id     INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    employee_id     INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    PRIMARY KEY (document_id, employee_id)
);

CREATE TABLE IF NOT EXISTS announcements (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT    NOT NULL,
    body            TEXT    NOT NULL,
    priority        TEXT    NOT NULL DEFAULT 'normal',
    audience        TEXT    NOT NULL DEFAULT 'all',
    department      TEXT,
    created_by      INTEGER REFERENCES employees(id),
    expires_at      TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS announcement_reads (
    announcement_id INTEGER NOT NULL REFERENCES announcements(id) ON DELETE CASCADE,
    employee_id     INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    read_at         TEXT    NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (announcement_id, employee_id)
);

CREATE TABLE IF NOT EXISTS wifi_sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id     INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    mac_address     TEXT    NOT NULL,
    connected_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    disconnected_at TEXT,
    ssid            TEXT
);

CREATE TABLE IF NOT EXISTS reports (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    report_type     TEXT    NOT NULL,
    period_start    TEXT    NOT NULL,
    period_end      TEXT    NOT NULL,
    generated_by    INTEGER REFERENCES employees(id),
    file_path       TEXT,
    payload_json    TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_id        INTEGER REFERENCES employees(id),
    action          TEXT    NOT NULL,
    target_table    TEXT,
    target_id       INTEGER,
    detail          TEXT,
    ip_address      TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS settings (
    key             TEXT    PRIMARY KEY,
    value           TEXT,
    description     TEXT,
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    token           TEXT    PRIMARY KEY,
    employee_id     INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    expires_at      TEXT    NOT NULL,
    ip_address      TEXT
);

"""

DEFAULT_SETTINGS = [
    ("company_name",      "The Rebar Company",   "Display name used across the app"),
    ("primary_color",     "#1565C0",             "Brand primary colour (blue)"),
    ("accent_color",      "#FF6F00",             "Brand accent colour (orange)"),
    ("timezone",          "Australia/Melbourne", "Payroll + report timezone"),
    ("week_start",        "Monday",              "First day of the work week"),
    ("pay_cycle",         "fortnightly",         "weekly | fortnightly | monthly"),
    ("face_threshold",    "0.50",                "Face-match confidence threshold (0-1)"),
    ("wifi_lock_enabled", "0",                   "Require office WiFi for clock-in (1=on)"),
    ("office_ssid",       "",                    "Office WiFi network name"),
    ("offline_mode",      "1",                   "Allow clock-in without internet (1=on)"),
    ("max_shift_hours",   "14",                  "Alert if a shift exceeds this many hours"),
]


# ─────────────────────────────────────────────
# INITIALISE
# ─────────────────────────────────────────────

def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        conn.executemany(
            "INSERT OR IGNORE INTO settings (key, value, description) VALUES (?, ?, ?)",
            DEFAULT_SETTINGS,
        )
        cur = conn.execute("SELECT COUNT(*) FROM employees WHERE role = 'admin'")
        if cur.fetchone()[0] == 0:
            _create_default_admin(conn)
        conn.commit()
        print(f"[DB] Initialised -> {DB_PATH}")
    finally:
        conn.close()


def _create_default_admin(conn):
    password_hash = _hash_password("admin1234")
    conn.execute(
        """INSERT INTO employees
               (employee_code, full_name, email, role, password_hash, is_active)
           VALUES (?, ?, ?, 'admin', ?, 1)""",
        ("RC-000", "System Admin", "admin@rebarcompany.com.au", password_hash),
    )
    print("[DB] Default admin created — email: admin@rebarcompany.com.au | password: admin1234")


# ─────────────────────────────────────────────
# UTILITY HELPERS
# ─────────────────────────────────────────────

def _hash_password(plain):
    salt = secrets.token_hex(16)
    h    = hashlib.sha256((salt + plain).encode()).hexdigest()
    return f"{salt}${h}"

def verify_password(plain, stored_hash):
    try:
        salt, h = stored_hash.split("$", 1)
        return hashlib.sha256((salt + plain).encode()).hexdigest() == h
    except ValueError:
        return False

def hash_pin(pin):
    return hashlib.sha256(pin.encode()).hexdigest()

def verify_pin(pin, stored_hash):
    return hashlib.sha256(pin.encode()).hexdigest() == stored_hash

def log_action(actor_id, action, target_table=None, target_id=None, detail=None, ip_address=None):
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO audit_log
                   (actor_id, action, target_table, target_id, detail, ip_address, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (actor_id, action, target_table, target_id, detail, ip_address, now_local()),
        )
        conn.commit()
    finally:
        conn.close()

def get_setting(key, default=None):
    conn = get_connection()
    try:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default
    finally:
        conn.close()

def set_setting(key, value):
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO settings (key, value, updated_at)
               VALUES (?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value,
                                              updated_at = excluded.updated_at""",
            (key, value, now_local()),
        )
        conn.commit()
    finally:
        conn.close()


# ─────────────────────────────────────────────
# EMPLOYEE HELPERS
# ─────────────────────────────────────────────

def get_employee_by_email(email):
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT * FROM employees WHERE email = ? AND is_active = 1", (email,)
        ).fetchone()
    finally:
        conn.close()

def get_employee_by_id(emp_id):
    conn = get_connection()
    try:
        return conn.execute("SELECT * FROM employees WHERE id = ?", (emp_id,)).fetchone()
    finally:
        conn.close()

def get_all_employees(active_only=True):
    conn = get_connection()
    try:
        q = "SELECT * FROM employees"
        if active_only:
            q += " WHERE is_active = 1"
        q += " ORDER BY full_name"
        return conn.execute(q).fetchall()
    finally:
        conn.close()

def next_employee_code():
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT employee_code FROM employees ORDER BY id DESC LIMIT 1"
        ).fetchone()
        num = int(row["employee_code"].split("-")[1]) + 1 if row else 1
        return f"RC-{num:03d}"
    finally:
        conn.close()


# ─────────────────────────────────────────────
# CLOCK HELPERS
# ─────────────────────────────────────────────

def clock_in(employee_id, method="manual", location=None, notes=None):
    conn = get_connection()
    try:
        open_record = conn.execute(
            "SELECT id FROM clock_records WHERE employee_id = ? AND clock_out IS NULL",
            (employee_id,),
        ).fetchone()
        if open_record:
            raise RuntimeError(f"Employee {employee_id} is already clocked in.")
        cur = conn.execute(
            """INSERT INTO clock_records (employee_id, clock_in, method, location, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (employee_id, now_local(), method, location, notes),
        )
        conn.commit()
        log_action(employee_id, "CLOCK_IN", "clock_records", cur.lastrowid, f"method={method}")
        return cur.lastrowid
    finally:
        conn.close()

def clock_out(employee_id, notes=None):
    conn = get_connection()
    try:
        record = conn.execute(
            "SELECT id, clock_in FROM clock_records WHERE employee_id = ? AND clock_out IS NULL",
            (employee_id,),
        ).fetchone()
        if not record:
            raise RuntimeError(f"Employee {employee_id} is not currently clocked in.")

        clock_in_dt = datetime.strptime(record["clock_in"], "%Y-%m-%d %H:%M:%S")
        now_dt      = datetime.now(TIMEZONE).replace(tzinfo=None)
        total_mins  = int((now_dt - clock_in_dt).total_seconds() / 60)

        conn.execute(
            """UPDATE clock_records
               SET clock_out = ?, total_minutes = ?, notes = COALESCE(?, notes)
               WHERE id = ?""",
            (now_local(), total_mins, notes, record["id"]),
        )
        conn.commit()
        log_action(employee_id, "CLOCK_OUT", "clock_records", record["id"],
                   f"total_minutes={total_mins}")
        return total_mins
    finally:
        conn.close()

def get_open_clock(employee_id):
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT * FROM clock_records WHERE employee_id = ? AND clock_out IS NULL",
            (employee_id,),
        ).fetchone()
    finally:
        conn.close()

def get_clock_records(employee_id, from_date, to_date):
    conn = get_connection()
    try:
        return conn.execute(
            """SELECT cr.*, e.full_name, e.employee_code
               FROM clock_records cr
               JOIN employees e ON e.id = cr.employee_id
               WHERE cr.employee_id = ?
                 AND DATE(cr.clock_in) BETWEEN DATE(?) AND DATE(?)
               ORDER BY cr.clock_in DESC""",
            (employee_id, from_date, to_date),
        ).fetchall()
    finally:
        conn.close()


# ─────────────────────────────────────────────
# SESSION HELPERS
# ─────────────────────────────────────────────

def create_session(employee_id, ip_address=None, hours=8):
    from datetime import timedelta
    token      = secrets.token_urlsafe(32)
    expires_at = (datetime.now(TIMEZONE) + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO sessions (token, employee_id, expires_at, ip_address, created_at) VALUES (?, ?, ?, ?, ?)",
            (token, employee_id, expires_at, ip_address, now_local()),
        )
        conn.commit()
    finally:
        conn.close()
    return token

def get_session(token):
    conn = get_connection()
    try:
        return conn.execute(
            """SELECT s.*, e.role, e.full_name, e.employee_code, e.id as employee_id
               FROM sessions s
               JOIN employees e ON e.id = s.employee_id
               WHERE s.token = ?
                 AND s.expires_at > ?""",
            (token, now_local()),
        ).fetchone()
    finally:
        conn.close()

def delete_session(token):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
    finally:
        conn.close()


# ─────────────────────────────────────────────
# ANNOUNCEMENT HELPERS
# ─────────────────────────────────────────────

def get_active_announcements(employee_id, department=None):
    conn = get_connection()
    try:
        return conn.execute(
            """SELECT a.*,
                      CASE WHEN ar.employee_id IS NOT NULL THEN 1 ELSE 0 END AS is_read
               FROM announcements a
               LEFT JOIN announcement_reads ar
                      ON ar.announcement_id = a.id AND ar.employee_id = ?
               WHERE (a.expires_at IS NULL OR a.expires_at > ?)
                 AND (a.audience = 'all'
                      OR (a.audience = 'department' AND a.department = ?))
               ORDER BY a.priority DESC, a.created_at DESC""",
            (employee_id, now_local(), department),
        ).fetchall()
    finally:
        conn.close()

def mark_announcement_read(announcement_id, employee_id):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO announcement_reads (announcement_id, employee_id, read_at) VALUES (?, ?, ?)",
            (announcement_id, employee_id, now_local()),
        )
        conn.commit()
    finally:
        conn.close()


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    init_db()