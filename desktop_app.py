"""
desktop_app.py — The Rebar Company
Desktop admin application built with CustomTkinter.
"""

import customtkinter as ctk
from tkinter import ttk, messagebox
import sys, os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import database as db

# ── Theme ──────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BLUE   = "#1565C0"
ORANGE = "#FF6F00"
BG     = "#0A0F1E"
SURFACE = "#111827"
TEXT   = "#F0F4FF"
MUTED  = "#8898AA"


# ────────────────────────────────────────────────────────────
# MAIN APP
# ────────────────────────────────────────────────────────────

class RebarAdminApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("The Rebar Company — Admin")
        self.geometry("1100x700")
        self.minsize(900, 600)
        self.configure(fg_color=BG)

        self.current_user = None
        self._build_login()

    # ── LOGIN SCREEN ────────────────────────────────────────

    def _build_login(self):
        self._clear()

        frame = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=12, width=400)
        frame.place(relx=0.5, rely=0.5, anchor="center")
        frame.grid_propagate(False)
        frame.configure(width=400, height=460)

        ctk.CTkLabel(frame, text="THE REBAR COMPANY",
                     font=ctk.CTkFont("Arial", 22, "bold"),
                     text_color=TEXT).place(relx=0.5, rely=0.12, anchor="center")

        ctk.CTkLabel(frame, text="Admin Desktop App",
                     font=ctk.CTkFont("Arial", 13),
                     text_color=MUTED).place(relx=0.5, rely=0.22, anchor="center")

        ctk.CTkLabel(frame, text="Email",
                     font=ctk.CTkFont("Arial", 12),
                     text_color=MUTED).place(relx=0.1, rely=0.34, anchor="w")
        self.email_entry = ctk.CTkEntry(frame, width=320, height=40,
                                        placeholder_text="admin@rebarcompany.com.au")
        self.email_entry.place(relx=0.5, rely=0.44, anchor="center")

        ctk.CTkLabel(frame, text="Password",
                     font=ctk.CTkFont("Arial", 12),
                     text_color=MUTED).place(relx=0.1, rely=0.54, anchor="w")
        self.pass_entry = ctk.CTkEntry(frame, width=320, height=40,
                                       placeholder_text="Password", show="*")
        self.pass_entry.place(relx=0.5, rely=0.64, anchor="center")

        self.login_error = ctk.CTkLabel(frame, text="",
                                        font=ctk.CTkFont("Arial", 11),
                                        text_color="#EF4444")
        self.login_error.place(relx=0.5, rely=0.74, anchor="center")

        ctk.CTkButton(frame, text="Sign In", width=320, height=42,
                      fg_color=ORANGE, hover_color="#E65100",
                      font=ctk.CTkFont("Arial", 14, "bold"),
                      command=self._do_login).place(relx=0.5, rely=0.86, anchor="center")

        self.pass_entry.bind("<Return>", lambda e: self._do_login())

    def _do_login(self):
        email    = self.email_entry.get().strip().lower()
        password = self.pass_entry.get()
        employee = db.get_employee_by_email(email)

        if employee and db.verify_password(password, employee["password_hash"]):
            if employee["role"] not in ("admin", "supervisor"):
                self.login_error.configure(text="Access denied — admin only.")
                return
            self.current_user = dict(employee)
            self._build_main()
        else:
            self.login_error.configure(text="Invalid email or password.")

    # ── MAIN LAYOUT ─────────────────────────────────────────

    def _build_main(self):
        self._clear()

        # Sidebar
        sidebar = ctk.CTkFrame(self, fg_color=SURFACE, width=200, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        ctk.CTkLabel(sidebar, text="REBAR CO",
                     font=ctk.CTkFont("Arial", 16, "bold"),
                     text_color=ORANGE).pack(pady=(28, 4))
        ctk.CTkLabel(sidebar, text="Admin Panel",
                     font=ctk.CTkFont("Arial", 11),
                     text_color=MUTED).pack(pady=(0, 24))

        self.nav_buttons = {}
        nav_items = [
            ("Overview",    self._show_overview),
            ("Employees",   self._show_employees),
            ("Timesheets",  self._show_timesheets),
            ("Clock Admin", self._show_clock_admin),
            ("Settings",    self._show_settings),
        ]

        for label, cmd in nav_items:
            btn = ctk.CTkButton(sidebar, text=label, width=160, height=36,
                                fg_color="transparent", hover_color="#1A2235",
                                text_color=MUTED, anchor="w",
                                font=ctk.CTkFont("Arial", 13),
                                command=lambda c=cmd, l=label: self._nav(c, l))
            btn.pack(pady=2, padx=16)
            self.nav_buttons[label] = btn

        # Logout
        ctk.CTkButton(sidebar, text="Sign Out", width=160, height=36,
                      fg_color="transparent", hover_color="#1A2235",
                      text_color="#EF4444", anchor="w",
                      font=ctk.CTkFont("Arial", 13),
                      command=self._build_login).pack(side="bottom", pady=20, padx=16)

        # Main content area
        self.content = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.content.pack(side="right", fill="both", expand=True)

        self._nav(self._show_overview, "Overview")

    def _nav(self, cmd, label):
        for l, btn in self.nav_buttons.items():
            btn.configure(text_color=MUTED, fg_color="transparent")
        self.nav_buttons[label].configure(text_color=TEXT, fg_color=BLUE)
        self._clear_content()
        cmd()

    def _clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()

    def _clear(self):
        for w in self.winfo_children():
            w.destroy()

    # ── OVERVIEW ────────────────────────────────────────────

    def _show_overview(self):
        frame = ctk.CTkScrollableFrame(self.content, fg_color=BG)
        frame.pack(fill="both", expand=True, padx=24, pady=24)

        ctk.CTkLabel(frame, text="Overview",
                     font=ctk.CTkFont("Arial", 24, "bold"),
                     text_color=TEXT).pack(anchor="w", pady=(0, 20))

        employees   = db.get_all_employees(active_only=False)
        active_emps = [e for e in employees if e["is_active"]]

        conn = db.get_connection()
        today_clocked = conn.execute(
            "SELECT DISTINCT employee_id FROM clock_records WHERE DATE(clock_in) = DATE('now')"
        ).fetchall()
        conn.close()
        clocked_ids = {r["employee_id"] for r in today_clocked}

        # Stats row
        stats_frame = ctk.CTkFrame(frame, fg_color="transparent")
        stats_frame.pack(fill="x", pady=(0, 20))

        stats = [
            ("Total Employees", str(len(employees))),
            ("Active",          str(len(active_emps))),
            ("Clocked In Today", str(len(clocked_ids))),
            ("Not In Yet",      str(len(active_emps) - len(clocked_ids))),
        ]

        for label, value in stats:
            card = ctk.CTkFrame(stats_frame, fg_color=SURFACE, corner_radius=8)
            card.pack(side="left", padx=6, pady=4, fill="y", expand=True)
            ctk.CTkLabel(card, text=value,
                         font=ctk.CTkFont("Arial", 28, "bold"),
                         text_color=ORANGE).pack(padx=20, pady=(16, 4))
            ctk.CTkLabel(card, text=label,
                         font=ctk.CTkFont("Arial", 11),
                         text_color=MUTED).pack(padx=20, pady=(0, 16))

        # Clocked in list
        ctk.CTkLabel(frame, text="Clocked In Today",
                     font=ctk.CTkFont("Arial", 15, "bold"),
                     text_color=TEXT).pack(anchor="w", pady=(10, 8))

        for e in active_emps:
            color = "#22C55E" if e["id"] in clocked_ids else "#EF4444"
            status = "IN" if e["id"] in clocked_ids else "OUT"
            row = ctk.CTkFrame(frame, fg_color=SURFACE, corner_radius=6)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=e["full_name"],
                         font=ctk.CTkFont("Arial", 13),
                         text_color=TEXT).pack(side="left", padx=16, pady=10)
            ctk.CTkLabel(row, text=e["employee_code"],
                         font=ctk.CTkFont("Arial", 11),
                         text_color=MUTED).pack(side="left", padx=8)
            ctk.CTkLabel(row, text=status,
                         font=ctk.CTkFont("Arial", 12, "bold"),
                         text_color=color).pack(side="right", padx=16)

    # ── EMPLOYEES ───────────────────────────────────────────

    def _show_employees(self):
        frame = ctk.CTkScrollableFrame(self.content, fg_color=BG)
        frame.pack(fill="both", expand=True, padx=24, pady=24)

        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(header, text="Employees",
                     font=ctk.CTkFont("Arial", 24, "bold"),
                     text_color=TEXT).pack(side="left")
        ctk.CTkButton(header, text="+ Add Employee", width=140, height=36,
                      fg_color=ORANGE, hover_color="#E65100",
                      command=self._add_employee_dialog).pack(side="right")

        employees = db.get_all_employees(active_only=False)

        cols = ["Code", "Name", "Role", "Department", "Email", "Status"]
        col_frame = ctk.CTkFrame(frame, fg_color=SURFACE, corner_radius=6)
        col_frame.pack(fill="x", pady=(0, 2))
        widths = [80, 160, 90, 120, 200, 70]
        for i, (col, w) in enumerate(zip(cols, widths)):
            ctk.CTkLabel(col_frame, text=col.upper(),
                         font=ctk.CTkFont("Arial", 10, "bold"),
                         text_color=MUTED, width=w, anchor="w").grid(
                row=0, column=i, padx=10, pady=8)

        for emp in employees:
            row = ctk.CTkFrame(frame, fg_color=SURFACE, corner_radius=4)
            row.pack(fill="x", pady=1)
            vals = [
                emp["employee_code"],
                emp["full_name"],
                emp["role"].capitalize(),
                emp["department"] or "—",
                emp["email"] or "—",
                "Active" if emp["is_active"] else "Inactive",
            ]
            for i, (val, w) in enumerate(zip(vals, widths)):
                color = "#4ADE80" if val == "Active" else ("#EF4444" if val == "Inactive" else TEXT)
                ctk.CTkLabel(row, text=val,
                             font=ctk.CTkFont("Arial", 12),
                             text_color=color, width=w, anchor="w").grid(
                    row=0, column=i, padx=10, pady=8)

    def _add_employee_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add Employee")
        dialog.geometry("460px x 520px")
        dialog.geometry("460x520")
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Add New Employee",
                     font=ctk.CTkFont("Arial", 18, "bold"),
                     text_color=TEXT).pack(pady=(20, 16))

        fields = {}
        for label, placeholder in [
            ("Full Name", "Jane Smith"),
            ("Email", "jane@rebarcompany.com.au"),
            ("Phone", "04XX XXX XXX"),
            ("Department", "Site / Office"),
            ("Password", "Temporary password"),
        ]:
            ctk.CTkLabel(dialog, text=label, text_color=MUTED,
                         font=ctk.CTkFont("Arial", 12)).pack(anchor="w", padx=24)
            entry = ctk.CTkEntry(dialog, width=400, height=36,
                                 placeholder_text=placeholder,
                                 show="*" if label == "Password" else "")
            entry.pack(pady=(2, 10), padx=24)
            fields[label] = entry

        role_var = ctk.StringVar(value="employee")
        ctk.CTkLabel(dialog, text="Role", text_color=MUTED,
                     font=ctk.CTkFont("Arial", 12)).pack(anchor="w", padx=24)
        ctk.CTkOptionMenu(dialog, values=["employee", "supervisor", "admin"],
                          variable=role_var, width=400).pack(pady=(2, 16), padx=24)

        error_label = ctk.CTkLabel(dialog, text="", text_color="#EF4444",
                                   font=ctk.CTkFont("Arial", 11))
        error_label.pack()

        def save():
            name  = fields["Full Name"].get().strip()
            email = fields["Email"].get().strip().lower()
            pwd   = fields["Password"].get().strip()

            if not name or not email or not pwd:
                error_label.configure(text="Name, email and password are required.")
                return

            code = db.next_employee_code()
            ph   = db._hash_password(pwd)
            conn = db.get_connection()
            try:
                conn.execute(
                    """INSERT INTO employees
                           (employee_code, full_name, email, phone, role,
                            department, password_hash, is_active)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
                    (code, name, email,
                     fields["Phone"].get().strip(),
                     role_var.get(),
                     fields["Department"].get().strip(),
                     ph)
                )
                conn.commit()
                messagebox.showinfo("Success", f"Employee {name} added with code {code}.")
                dialog.destroy()
                self._show_employees()
            except Exception as e:
                error_label.configure(text=str(e))
            finally:
                conn.close()

        ctk.CTkButton(dialog, text="Create Employee", width=400, height=40,
                      fg_color=ORANGE, hover_color="#E65100",
                      command=save).pack(pady=8, padx=24)

    # ── TIMESHEETS ──────────────────────────────────────────

    def _show_timesheets(self):
        frame = ctk.CTkScrollableFrame(self.content, fg_color=BG)
        frame.pack(fill="both", expand=True, padx=24, pady=24)

        ctk.CTkLabel(frame, text="Timesheets",
                     font=ctk.CTkFont("Arial", 24, "bold"),
                     text_color=TEXT).pack(anchor="w", pady=(0, 16))

        # Filter bar
        filter_frame = ctk.CTkFrame(frame, fg_color=SURFACE, corner_radius=8)
        filter_frame.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(filter_frame, text="From:", text_color=MUTED).grid(row=0, column=0, padx=12, pady=10)
        from_entry = ctk.CTkEntry(filter_frame, width=120, placeholder_text="YYYY-MM-DD")
        from_entry.insert(0, datetime.now().strftime("%Y-%m-01"))
        from_entry.grid(row=0, column=1, padx=6, pady=10)

        ctk.CTkLabel(filter_frame, text="To:", text_color=MUTED).grid(row=0, column=2, padx=12)
        to_entry = ctk.CTkEntry(filter_frame, width=120, placeholder_text="YYYY-MM-DD")
        to_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        to_entry.grid(row=0, column=3, padx=6, pady=10)

        results_frame = ctk.CTkFrame(frame, fg_color="transparent")
        results_frame.pack(fill="x")

        def load():
            for w in results_frame.winfo_children():
                w.destroy()

            conn = db.get_connection()
            records = conn.execute(
                """SELECT cr.*, e.full_name, e.employee_code
                   FROM clock_records cr
                   JOIN employees e ON e.id = cr.employee_id
                   WHERE DATE(cr.clock_in) BETWEEN DATE(?) AND DATE(?)
                   ORDER BY cr.clock_in DESC""",
                (from_entry.get(), to_entry.get())
            ).fetchall()
            conn.close()

            total_mins = sum(r["total_minutes"] or 0 for r in records)

            ctk.CTkLabel(results_frame,
                         text=f"{len(records)} shifts  |  Total: {total_mins // 60}h {total_mins % 60}m",
                         font=ctk.CTkFont("Arial", 13), text_color=MUTED).pack(anchor="w", pady=(0, 8))

            cols = ["Employee", "Date", "Clock In", "Clock Out", "Duration", "Method"]
            header = ctk.CTkFrame(results_frame, fg_color=SURFACE, corner_radius=6)
            header.pack(fill="x", pady=(0, 2))
            widths = [160, 100, 80, 80, 90, 80]
            for i, (col, w) in enumerate(zip(cols, widths)):
                ctk.CTkLabel(header, text=col.upper(),
                             font=ctk.CTkFont("Arial", 10, "bold"),
                             text_color=MUTED, width=w, anchor="w").grid(
                    row=0, column=i, padx=10, pady=8)

            for r in records:
                row = ctk.CTkFrame(results_frame, fg_color=SURFACE, corner_radius=4)
                row.pack(fill="x", pady=1)
                dur = f"{(r['total_minutes'] or 0) // 60}h {(r['total_minutes'] or 0) % 60}m" if r["total_minutes"] else "Active"
                vals = [r["full_name"], r["clock_in"][:10], r["clock_in"][11:16],
                        r["clock_out"][11:16] if r["clock_out"] else "—", dur, r["method"] or "manual"]
                for i, (val, w) in enumerate(zip(vals, widths)):
                    ctk.CTkLabel(row, text=val,
                                 font=ctk.CTkFont("Arial", 12),
                                 text_color=TEXT, width=w, anchor="w").grid(
                        row=0, column=i, padx=10, pady=8)

        ctk.CTkButton(filter_frame, text="Load", width=80, height=32,
                      fg_color=BLUE, command=load).grid(row=0, column=4, padx=12)
        load()

    # ── CLOCK ADMIN ─────────────────────────────────────────

    def _show_clock_admin(self):
        frame = ctk.CTkScrollableFrame(self.content, fg_color=BG)
        frame.pack(fill="both", expand=True, padx=24, pady=24)

        ctk.CTkLabel(frame, text="Clock Admin",
                     font=ctk.CTkFont("Arial", 24, "bold"),
                     text_color=TEXT).pack(anchor="w", pady=(0, 16))

        ctk.CTkLabel(frame, text="Manually clock employees in or out",
                     font=ctk.CTkFont("Arial", 13), text_color=MUTED).pack(anchor="w", pady=(0, 16))

        employees = db.get_all_employees()

        for emp in employees:
            open_clock = db.get_open_clock(emp["id"])
            row = ctk.CTkFrame(frame, fg_color=SURFACE, corner_radius=6)
            row.pack(fill="x", pady=3)

            ctk.CTkLabel(row, text=emp["full_name"],
                         font=ctk.CTkFont("Arial", 13, "bold"),
                         text_color=TEXT).pack(side="left", padx=16, pady=12)
            ctk.CTkLabel(row, text=emp["employee_code"],
                         font=ctk.CTkFont("Arial", 11), text_color=MUTED).pack(side="left", padx=4)

            if open_clock:
                ctk.CTkLabel(row, text=f"IN since {open_clock['clock_in'][11:16]}",
                             font=ctk.CTkFont("Arial", 11),
                             text_color="#4ADE80").pack(side="left", padx=12)
                ctk.CTkButton(row, text="Clock Out", width=100, height=30,
                              fg_color="#EF4444", hover_color="#DC2626",
                              command=lambda eid=emp["id"]: self._manual_clock_out(eid)
                              ).pack(side="right", padx=16)
            else:
                ctk.CTkLabel(row, text="Not clocked in",
                             font=ctk.CTkFont("Arial", 11),
                             text_color=MUTED).pack(side="left", padx=12)
                ctk.CTkButton(row, text="Clock In", width=100, height=30,
                              fg_color="#22C55E", hover_color="#16A34A",
                              command=lambda eid=emp["id"]: self._manual_clock_in(eid)
                              ).pack(side="right", padx=16)

    def _manual_clock_in(self, emp_id):
        try:
            db.clock_in(emp_id, method="manual")
            self._show_clock_admin()
        except RuntimeError as e:
            messagebox.showerror("Error", str(e))

    def _manual_clock_out(self, emp_id):
        try:
            mins = db.clock_out(emp_id)
            messagebox.showinfo("Clocked Out", f"Clocked out — {mins // 60}h {mins % 60}m worked.")
            self._show_clock_admin()
        except RuntimeError as e:
            messagebox.showerror("Error", str(e))

    # ── SETTINGS ────────────────────────────────────────────

    def _show_settings(self):
        frame = ctk.CTkScrollableFrame(self.content, fg_color=BG)
        frame.pack(fill="both", expand=True, padx=24, pady=24)

        ctk.CTkLabel(frame, text="Settings",
                     font=ctk.CTkFont("Arial", 24, "bold"),
                     text_color=TEXT).pack(anchor="w", pady=(0, 20))

        settings_keys = [
            ("company_name",      "Company Name"),
            ("timezone",          "Timezone"),
            ("pay_cycle",         "Pay Cycle"),
            ("office_ssid",       "Office WiFi SSID"),
            ("max_shift_hours",   "Max Shift Hours"),
            ("face_threshold",    "Face Match Threshold"),
        ]

        entries = {}
        for key, label in settings_keys:
            ctk.CTkLabel(frame, text=label, text_color=MUTED,
                         font=ctk.CTkFont("Arial", 12)).pack(anchor="w", pady=(8, 2))
            entry = ctk.CTkEntry(frame, width=400, height=36)
            entry.insert(0, db.get_setting(key, ""))
            entry.pack(anchor="w", pady=(0, 4))
            entries[key] = entry

        # WiFi lock toggle
        ctk.CTkLabel(frame, text="WiFi Lock", text_color=MUTED,
                     font=ctk.CTkFont("Arial", 12)).pack(anchor="w", pady=(8, 2))
        wifi_var = ctk.StringVar(value=db.get_setting("wifi_lock_enabled", "0"))
        ctk.CTkOptionMenu(frame, values=["0 - Disabled", "1 - Enabled"],
                          variable=wifi_var, width=400).pack(anchor="w", pady=(0, 16))

        error_label = ctk.CTkLabel(frame, text="", text_color="#4ADE80",
                                   font=ctk.CTkFont("Arial", 12))
        error_label.pack(anchor="w")

        def save():
            for key, entry in entries.items():
                db.set_setting(key, entry.get().strip())
            db.set_setting("wifi_lock_enabled", wifi_var.get()[0])
            error_label.configure(text="Settings saved successfully!")

        ctk.CTkButton(frame, text="Save Settings", width=200, height=40,
                      fg_color=ORANGE, hover_color="#E65100",
                      command=save).pack(anchor="w", pady=8)


# ────────────────────────────────────────────────────────────
# ENTRY POINT
# ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    db.init_db()
    app = RebarAdminApp()
    app.mainloop()