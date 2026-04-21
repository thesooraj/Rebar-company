from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from datetime import datetime
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import database as db
import reports as rp

app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
app.secret_key = "rebar-dev-secret-change-in-prod"


# ────────────────────────────────────────────────────────────
# HELPERS
# ────────────────────────────────────────────────────────────

def current_employee():
    token = session.get("token")
    if not token:
        return None
    return db.get_session(token)


def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_employee():
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        emp = current_employee()
        if not emp or emp["role"] not in ("admin", "supervisor"):
            flash("Access denied.", "danger")
            return redirect(url_for("dashboard"))
        return fn(*args, **kwargs)
    return wrapper


# ────────────────────────────────────────────────────────────
# AUTH
# ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if current_employee():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_employee():
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        employee = db.get_employee_by_email(email)
        if employee and db.verify_password(password, employee["password_hash"]):
            token = db.create_session(employee["id"], ip_address=request.remote_addr, hours=10)
            session["token"] = token
            db.log_action(employee["id"], "LOGIN", detail=f"ip={request.remote_addr}")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    token = session.pop("token", None)
    if token:
        db.delete_session(token)
    return redirect(url_for("login"))


# ────────────────────────────────────────────────────────────
# DASHBOARD
# ────────────────────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    emp           = current_employee()
    open_clock    = db.get_open_clock(emp["employee_id"])
    announcements = db.get_active_announcements(emp["employee_id"])
    today         = datetime.utcnow().strftime("%Y-%m-%d")
    today_records = db.get_clock_records(emp["employee_id"], today, today)
    today_total   = sum(r["total_minutes"] or 0 for r in today_records)
    return render_template("dashboard.html", emp=emp, open_clock=open_clock,
                           announcements=announcements, today_records=today_records,
                           today_total=today_total)


# ────────────────────────────────────────────────────────────
# CLOCK API
# ────────────────────────────────────────────────────────────

@app.route("/api/clock-in", methods=["POST"])
@login_required
def api_clock_in():
    emp = current_employee()
    try:
        record_id = db.clock_in(emp["employee_id"], method="manual")
        return jsonify({"ok": True, "record_id": record_id})
    except RuntimeError as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/api/clock-out", methods=["POST"])
@login_required
def api_clock_out():
    emp = current_employee()
    try:
        minutes = db.clock_out(emp["employee_id"])
        return jsonify({"ok": True, "total_minutes": minutes,
                        "display": f"{minutes // 60}h {minutes % 60}m"})
    except RuntimeError as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/api/mark-read/<int:announcement_id>", methods=["POST"])
@login_required
def api_mark_read(announcement_id):
    emp = current_employee()
    db.mark_announcement_read(announcement_id, emp["employee_id"])
    return jsonify({"ok": True})


# ────────────────────────────────────────────────────────────
# TIMESHEET
# ────────────────────────────────────────────────────────────

@app.route("/timesheet")
@login_required
def timesheet():
    emp        = current_employee()
    from_date  = request.args.get("from", datetime.utcnow().strftime("%Y-%m-01"))
    to_date    = request.args.get("to",   datetime.utcnow().strftime("%Y-%m-%d"))
    records    = db.get_clock_records(emp["employee_id"], from_date, to_date)
    total_mins = sum(r["total_minutes"] or 0 for r in records)
    return render_template("timesheet.html", emp=emp, records=records,
                           from_date=from_date, to_date=to_date,
                           total_hours=total_mins // 60, total_mins=total_mins % 60)


# ────────────────────────────────────────────────────────────
# ADMIN — OVERVIEW
# ────────────────────────────────────────────────────────────

@app.route("/admin")
@login_required
@admin_required
def admin_home():
    emp           = current_employee()
    employees     = db.get_all_employees(active_only=False)
    today         = datetime.utcnow().strftime("%Y-%m-%d")
    announcements = db.get_active_announcements(emp["employee_id"])
    conn          = db.get_connection()
    today_clocked = conn.execute(
        "SELECT DISTINCT employee_id FROM clock_records WHERE DATE(clock_in) = DATE('now')"
    ).fetchall()
    conn.close()
    clocked_ids = {r["employee_id"] for r in today_clocked}
    return render_template("admin/home.html", emp=emp, employees=employees,
                           clocked_ids=clocked_ids, announcements=announcements,
                           today=today)


# ────────────────────────────────────────────────────────────
# ADMIN — EMPLOYEES
# ────────────────────────────────────────────────────────────

@app.route("/admin/employees")
@login_required
@admin_required
def admin_employees():
    emp       = current_employee()
    employees = db.get_all_employees(active_only=False)
    return render_template("admin/employees.html", emp=emp, employees=employees)


@app.route("/admin/employees/add", methods=["GET", "POST"])
@login_required
@admin_required
def admin_add_employee():
    emp = current_employee()
    if request.method == "POST":
        full_name  = request.form.get("full_name", "").strip()
        email      = request.form.get("email", "").strip().lower()
        phone      = request.form.get("phone", "").strip()
        role       = request.form.get("role", "employee")
        department = request.form.get("department", "").strip()
        password   = request.form.get("password", "").strip()
        pin        = request.form.get("pin", "").strip()

        if not full_name or not email or not password:
            flash("Name, email and password are required.", "danger")
            return render_template("admin/add_employee.html", emp=emp)

        code          = db.next_employee_code()
        password_hash = db._hash_password(password)
        pin_hash      = db.hash_pin(pin) if pin else None

        conn = db.get_connection()
        try:
            conn.execute(
                """INSERT INTO employees
                       (employee_code, full_name, email, phone, role,
                        department, password_hash, pin_hash, is_active)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                (code, full_name, email, phone, role, department, password_hash, pin_hash)
            )
            conn.commit()
            flash(f"Employee {full_name} added with code {code}.", "success")
            return redirect(url_for("admin_employees"))
        except Exception as e:
            flash(f"Error: {str(e)}", "danger")
        finally:
            conn.close()

    return render_template("admin/add_employee.html", emp=emp)


@app.route("/admin/employees/<int:emp_id>/toggle", methods=["POST"])
@login_required
@admin_required
def admin_toggle_employee(emp_id):
    conn = db.get_connection()
    try:
        row = conn.execute("SELECT is_active FROM employees WHERE id = ?", (emp_id,)).fetchone()
        if row:
            new_status = 0 if row["is_active"] else 1
            conn.execute("UPDATE employees SET is_active = ? WHERE id = ?", (new_status, emp_id))
            conn.commit()
            flash("Employee status updated.", "success")
    finally:
        conn.close()
    return redirect(url_for("admin_employees"))


# ────────────────────────────────────────────────────────────
# ADMIN — TIMESHEETS
# ────────────────────────────────────────────────────────────

@app.route("/admin/timesheets")
@login_required
@admin_required
def admin_timesheets():
    emp       = current_employee()
    from_date = request.args.get("from", datetime.utcnow().strftime("%Y-%m-01"))
    to_date   = request.args.get("to",   datetime.utcnow().strftime("%Y-%m-%d"))
    emp_id    = request.args.get("emp_id", "all")
    employees = db.get_all_employees()

    conn = db.get_connection()
    if emp_id == "all":
        records = conn.execute(
            """SELECT cr.*, e.full_name, e.employee_code
               FROM clock_records cr
               JOIN employees e ON e.id = cr.employee_id
               WHERE DATE(cr.clock_in) BETWEEN DATE(?) AND DATE(?)
               ORDER BY cr.clock_in DESC""",
            (from_date, to_date)
        ).fetchall()
    else:
        records = conn.execute(
            """SELECT cr.*, e.full_name, e.employee_code
               FROM clock_records cr
               JOIN employees e ON e.id = cr.employee_id
               WHERE cr.employee_id = ?
                 AND DATE(cr.clock_in) BETWEEN DATE(?) AND DATE(?)
               ORDER BY cr.clock_in DESC""",
            (emp_id, from_date, to_date)
        ).fetchall()
    conn.close()

    total_mins = sum(r["total_minutes"] or 0 for r in records)
    return render_template("admin/timesheets.html", emp=emp, records=records,
                           employees=employees, from_date=from_date, to_date=to_date,
                           emp_id=emp_id, total_hours=total_mins // 60,
                           total_mins=total_mins % 60)


# ────────────────────────────────────────────────────────────
# ADMIN — ANNOUNCEMENTS
# ────────────────────────────────────────────────────────────

@app.route("/admin/announcements", methods=["GET", "POST"])
@login_required
@admin_required
def admin_announcements():
    emp = current_employee()
    if request.method == "POST":
        title    = request.form.get("title", "").strip()
        body     = request.form.get("body", "").strip()
        priority = request.form.get("priority", "normal")
        audience = request.form.get("audience", "all")
        expires  = request.form.get("expires", "") or None

        if not title or not body:
            flash("Title and message are required.", "danger")
        else:
            conn = db.get_connection()
            try:
                conn.execute(
                    """INSERT INTO announcements
                           (title, body, priority, audience, created_by, expires_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (title, body, priority, audience, emp["employee_id"], expires)
                )
                conn.commit()
                flash("Announcement posted.", "success")
            finally:
                conn.close()

    conn = db.get_connection()
    announcements = conn.execute(
        """SELECT a.*, e.full_name as author
           FROM announcements a
           LEFT JOIN employees e ON e.id = a.created_by
           ORDER BY a.created_at DESC"""
    ).fetchall()
    conn.close()
    return render_template("admin/announcements.html", emp=emp, announcements=announcements)


@app.route("/admin/announcements/<int:ann_id>/delete", methods=["POST"])
@login_required
@admin_required
def admin_delete_announcement(ann_id):
    conn = db.get_connection()
    try:
        conn.execute("DELETE FROM announcements WHERE id = ?", (ann_id,))
        conn.commit()
        flash("Announcement deleted.", "success")
    finally:
        conn.close()
    return redirect(url_for("admin_announcements"))


# ────────────────────────────────────────────────────────────
# ADMIN — REPORTS
# ────────────────────────────────────────────────────────────

@app.route("/admin/reports", methods=["GET", "POST"])
@login_required
@admin_required
def admin_reports():
    emp = current_employee()

    if request.method == "POST":
        period_type = request.form.get("period_type", "weekly")
        from_date   = request.form.get("from_date", "")
        to_date     = request.form.get("to_date", "")

        if not from_date or not to_date:
            from_date, to_date = rp.get_period_dates(period_type)

        try:
            filepath = rp.generate_report(
                period_type=period_type,
                from_date=from_date,
                to_date=to_date,
                generated_by=emp["employee_id"]
            )
            return send_file(filepath, as_attachment=True,
                             download_name=os.path.basename(filepath),
                             mimetype="application/pdf")
        except Exception as e:
            flash(f"Error generating report: {str(e)}", "danger")

    # Get past reports
    conn = db.get_connection()
    past_reports = conn.execute(
        """SELECT r.*, e.full_name as generated_by_name
           FROM reports r
           LEFT JOIN employees e ON e.id = r.generated_by
           ORDER BY r.created_at DESC LIMIT 20"""
    ).fetchall()
    conn.close()

    weekly_start, weekly_end         = rp.get_period_dates("weekly")
    fortnightly_start, fortnightly_end = rp.get_period_dates("fortnightly")

    return render_template("admin/reports.html", emp=emp,
                           past_reports=past_reports,
                           weekly_start=weekly_start, weekly_end=weekly_end,
                           fortnightly_start=fortnightly_start,
                           fortnightly_end=fortnightly_end)


@app.route("/admin/reports/download/<path:filename>")
@login_required
@admin_required
def download_report(filename):
    filepath = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "database", "reports", filename
    )
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, mimetype="application/pdf")
    flash("Report file not found.", "danger")
    return redirect(url_for("admin_reports"))


# ────────────────────────────────────────────────────────────
# ENTRY POINT
# ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    db.init_db()
    app.run(debug=True, port=5000)