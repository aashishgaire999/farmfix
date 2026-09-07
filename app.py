#!/usr/bin/env python3
"""
FarmFix — Farm Equipment Repair & Maintenance Tracker
COMP 368 Database Systems, Project 1
Team: Ayush Gaire, Ashish Gaire, AJ Rayamajhi

A Flask application backed by a real SQLite3 database file. Every button in
the interface runs an actual SQL statement against database/farmfix.db. There
is no localStorage, no JSON file, and no hosted database anywhere in this
project.

Run with:   python app.py     (then open http://127.0.0.1:5000)
"""

import csv
import io
import os
import re
import sqlite3
from datetime import date, timedelta

from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DB_PATH = os.path.join(BASE_DIR, "database", "farmfix.db")

# Vercel Functions ship the project files as read-only. For the public demo,
# copy the seeded SQLite database to the function's writable /tmp directory.
# The demo copy can reset after a cold start or deployment; the repository's
# original database is never changed by website visitors.
if os.environ.get("VERCEL"):
    DB_PATH = "/tmp/farmfix.db"
    if not os.path.exists(DB_PATH):
        connection = sqlite3.connect(DB_PATH)
        try:
            with open(os.path.join(BASE_DIR, "database", "schema.sql")) as schema_file:
                connection.executescript(schema_file.read())
            with open(os.path.join(BASE_DIR, "database", "sample_data.sql")) as sample_file:
                connection.executescript(sample_file.read())
            connection.commit()
        finally:
            connection.close()
else:
    DB_PATH = SOURCE_DB_PATH

app = Flask(__name__)
app.config["SECRET_KEY"] = "comp368-farmfix-project1"
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2 MB cap on CSV uploads

# These lists must match the CHECK constraints in database/schema.sql.
EQUIPMENT_TYPES = [
    "Tractor", "Combine", "Planter", "Sprayer", "Baler",
    "Tillage", "Loader", "Truck", "Irrigation", "Other",
]
EQUIPMENT_STATUSES = [
    "Operational", "Needs Repair", "In Repair", "Out of Service", "Retired",
]
SERVICE_TYPES = [
    "Oil Change", "Filter Replacement", "Tire Inspection", "Engine Service",
    "Hydraulic Service", "Grease / Lubrication", "Coolant Service",
    "Belt / Chain Service", "General Inspection", "Other",
]


@app.route("/style.css")
def stylesheet():
    """Serve CSS locally; Vercel serves the same path from public/style.css."""
    return send_from_directory(os.path.join(BASE_DIR, "static"), "style.css")

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
EARLIEST_DATE = "1900-01-01"
LATEST_DATE = "2100-12-31"


def like_term(text):
    """Wrap a search term for LIKE, escaping the wildcards % and _.

    Without this, typing a literal '%' into the search box matches every row,
    because LIKE reads it as "any sequence of characters" -- and '_' matches
    any single character, so '_' also matches everything. Serial numbers and
    model codes genuinely contain underscores, so this is not hypothetical.
    Every query using it must add  ESCAPE '\\'  to the LIKE clause.
    """
    escaped = (
        str(text).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    )
    return f"%{escaped}%"


def parse_money(raw, label, errors):
    """Read a currency amount, tolerating '$', thousands commas and spaces.

    People copy figures straight off an invoice, and a spreadsheet export
    writes 1,240.75 rather than 1240.75. float() rejects both.
    """
    text = str(raw or "").strip().replace("$", "").replace(",", "").replace(" ", "")
    if not text:
        return 0.0
    try:
        value = round(float(text), 2)
    except (ValueError, OverflowError):
        errors.append(f"{label} '{raw}' is not a number")
        return None
    if value != value or value in (float("inf"), float("-inf")):
        errors.append(f"{label} '{raw}' is not a usable number")
        return None
    if value < 0:
        errors.append(f"{label} cannot be negative")
        return None
    return value


def check_date(value, label, errors, allow_future=False, required=True):
    """Validate an ISO date, and sanity-check the year.

    Checking only the FORMAT is not enough: '2099-01-01' and '1899-01-01' are
    both well-formed and both certainly typing mistakes. A repair or a service
    is something that already happened, so it cannot be in the future; a
    scheduled next-service date can be.
    """
    if not value:
        if required:
            errors.append(f"{label} is required")
        return
    if not DATE_RE.match(value):
        errors.append(f"{label} '{value}' must be in YYYY-MM-DD format")
        return
    if value < EARLIEST_DATE:
        errors.append(f"{label} '{value}' is before 1900 — check the year")
    elif not allow_future and value > date.today().isoformat():
        errors.append(f"{label} '{value}' is in the future")
    elif value > LATEST_DATE:
        errors.append(f"{label} '{value}' is after 2100 — check the year")

# Column names cannot be passed as bound parameters, so a user-supplied sort
# key is mapped through a whitelist the programmer controls instead of being
# pasted into the SQL string. That is what keeps ORDER BY injection-safe.
EQUIPMENT_SORTS = {
    "name": "e.name",
    "type": "e.equipment_type",
    "manufacturer": "e.manufacturer",
    "year": "e.year",
    "status": "e.status",
    "repair_cost": "total_repair_cost",
    "repairs": "repair_count",
}
REPAIR_SORTS = {
    "date": "r.repair_date",
    "cost": "r.cost",
    "equipment": "e.name",
    "mechanic": "mechanic_name",
    "problem": "r.problem",
}
MAINTENANCE_SORTS = {
    "date": "m.service_date",
    "cost": "m.cost",
    "equipment": "e.name",
    "type": "m.service_type",
    "next": "m.next_service_date",
}


# ---------------------------------------------------------------------------
# 1. SQLITE3 CONNECTION HANDLING
# ---------------------------------------------------------------------------
def get_db():
    """Open (or reuse) the SQLite3 connection for this request.

    sqlite3.connect() opens the database file directly. There is no server
    process, no host, no port and no credentials -- that is the core
    difference between SQLite3 and a server-based DBMS such as MySQL.
    """
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        # sqlite3.Row lets templates read columns by name: row["name"].
        g.db.row_factory = sqlite3.Row
        # SQLite defaults foreign key enforcement to OFF, and the setting
        # lives on the CONNECTION, not in the file. Without this line the
        # FOREIGN KEY clauses in schema.sql would be documentation only.
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db


@app.teardown_appcontext
def close_db(_exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query_all(sql, params=()):
    return get_db().execute(sql, params).fetchall()


def query_one(sql, params=()):
    return get_db().execute(sql, params).fetchone()


def execute(sql, params=()):
    """Run an INSERT / UPDATE / DELETE and commit it."""
    db = get_db()
    cur = db.execute(sql, params)
    db.commit()
    return cur


@app.context_processor
def inject_globals():
    return {
        "today_iso": date.today().isoformat(),
        "current_year": date.today().year,
        "equipment_types": EQUIPMENT_TYPES,
        "equipment_statuses": EQUIPMENT_STATUSES,
        "service_types": SERVICE_TYPES,
    }


@app.template_filter("money")
def money(value):
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


@app.template_filter("nice_date")
def nice_date(value):
    """'2026-09-04' -> 'Sep 4, 2026'. Left alone if it is not an ISO date."""
    if not value or not DATE_RE.match(str(value)):
        return value or "—"
    try:
        y, m, d = (int(p) for p in str(value).split("-"))
        return f"{date(y, m, d):%b} {d}, {y}"
    except ValueError:
        return value


def all_equipment():
    return query_all(
        "SELECT equipment_id, name, manufacturer, model FROM equipment ORDER BY name;"
    )


def all_mechanics():
    return query_all("SELECT mechanic_id, name, shop FROM mechanics ORDER BY name;")


# ---------------------------------------------------------------------------
# 2. VALIDATION  (shared by the web forms and the CSV importer)
# ---------------------------------------------------------------------------
def validate_equipment(row, existing_id=None):
    """Return (cleaned, [errors]) for one piece of equipment."""
    errors = []
    name = (row.get("name") or "").strip()
    etype = (row.get("equipment_type") or "").strip() or "Tractor"
    manufacturer = (row.get("manufacturer") or "").strip()
    model = (row.get("model") or "").strip()
    raw_year = str(row.get("year") or "").strip()
    serial = (row.get("serial_number") or "").strip()
    purchase = (row.get("purchase_date") or "").strip()
    status = (row.get("status") or "").strip() or "Operational"

    if not name:
        errors.append("name is required")
    elif len(name) > 100:
        errors.append("name must be 100 characters or fewer")
    if not manufacturer:
        errors.append("manufacturer is required")
    if etype not in EQUIPMENT_TYPES:
        errors.append(f"equipment type '{etype}' is not one of {EQUIPMENT_TYPES}")
    if status not in EQUIPMENT_STATUSES:
        errors.append(f"status '{status}' is not one of {EQUIPMENT_STATUSES}")

    year = None
    if raw_year:
        try:
            year = int(raw_year)
            if not 1900 <= year <= 2100:
                errors.append("year must be between 1900 and 2100")
        except ValueError:
            errors.append(f"year '{raw_year}' is not a whole number")

    check_date(purchase, "purchase date", errors, required=False)

    # serial_number is UNIQUE in the database. Checking here as well turns a
    # crash into a readable message, and lets the CSV importer report the row.
    if serial:
        if existing_id:
            clash = query_one(
                "SELECT equipment_id FROM equipment "
                "WHERE serial_number = ? AND equipment_id <> ?;",
                (serial, existing_id),
            )
        else:
            clash = query_one(
                "SELECT equipment_id FROM equipment WHERE serial_number = ?;",
                (serial,),
            )
        if clash:
            errors.append(f"serial number '{serial}' is already registered")

    cleaned = {
        "name": name,
        "equipment_type": etype,
        "manufacturer": manufacturer,
        "model": model or None,
        "year": year,
        "serial_number": serial or None,
        "purchase_date": purchase or None,
        "status": status,
    }
    return cleaned, errors


def validate_repair(row):
    errors = []
    equipment_id = (str(row.get("equipment_id") or "")).strip()
    mechanic_id = (str(row.get("mechanic_id") or "")).strip()
    repair_date = (row.get("repair_date") or "").strip()
    problem = (row.get("problem") or "").strip()
    description = (row.get("repair_description") or "").strip()
    raw_cost = str(row.get("cost") or "").strip()
    notes = (row.get("notes") or "").strip()

    if not equipment_id:
        errors.append("equipment is required — a repair must belong to a machine")
    elif not query_one(
        "SELECT equipment_id FROM equipment WHERE equipment_id = ?;", (equipment_id,)
    ):
        errors.append(f"no equipment with id {equipment_id}")

    if mechanic_id and not query_one(
        "SELECT mechanic_id FROM mechanics WHERE mechanic_id = ?;", (mechanic_id,)
    ):
        errors.append(f"no mechanic with id {mechanic_id}")

    if not problem:
        errors.append("problem description is required")
    check_date(repair_date, "repair date", errors)

    cost = parse_money(raw_cost, "cost", errors)

    cleaned = {
        "equipment_id": equipment_id or None,
        "mechanic_id": int(mechanic_id) if mechanic_id else None,
        "repair_date": repair_date,
        "problem": problem,
        "repair_description": description or None,
        "cost": cost,
        "notes": notes or None,
    }
    return cleaned, errors


def validate_maintenance(row):
    errors = []
    equipment_id = (str(row.get("equipment_id") or "")).strip()
    service_date = (row.get("service_date") or "").strip()
    service_type = (row.get("service_type") or "").strip()
    description = (row.get("description") or "").strip()
    raw_cost = str(row.get("cost") or "").strip()
    next_date = (row.get("next_service_date") or "").strip()
    notes = (row.get("notes") or "").strip()

    if not equipment_id:
        errors.append("equipment is required — a service record must belong to a machine")
    elif not query_one(
        "SELECT equipment_id FROM equipment WHERE equipment_id = ?;", (equipment_id,)
    ):
        errors.append(f"no equipment with id {equipment_id}")

    if service_type not in SERVICE_TYPES:
        errors.append(f"service type '{service_type}' is not one of {SERVICE_TYPES}")
    check_date(service_date, "service date", errors)
    # The follow-up date is the one place a future date is correct.
    check_date(next_date, "next service date", errors,
               allow_future=True, required=False)
    if next_date and DATE_RE.match(service_date) and next_date < service_date:
        errors.append("next service date cannot be before the service date")

    cost = parse_money(raw_cost, "cost", errors)

    cleaned = {
        "equipment_id": equipment_id or None,
        "service_date": service_date,
        "service_type": service_type,
        "description": description or None,
        "cost": cost,
        "next_service_date": next_date or None,
        "notes": notes or None,
    }
    return cleaned, errors


# ---------------------------------------------------------------------------
# 3. DASHBOARD
# ---------------------------------------------------------------------------
SQL_DASH_COUNTS = """
SELECT (SELECT COUNT(*) FROM equipment)   AS equipment_count,
       (SELECT COUNT(*) FROM repairs)     AS repair_count,
       (SELECT COUNT(*) FROM maintenance) AS maintenance_count,
       (SELECT COUNT(*) FROM mechanics)   AS mechanic_count,
       (SELECT COALESCE(SUM(cost), 0) FROM repairs)     AS total_repair_cost,
       (SELECT COALESCE(SUM(cost), 0) FROM maintenance) AS total_maintenance_cost,
       (SELECT COALESCE(AVG(cost), 0) FROM repairs)     AS avg_repair_cost,
       (SELECT COALESCE(MAX(cost), 0) FROM repairs)     AS max_repair_cost;
"""

# Upcoming and overdue service. next_service_date is nullable -- a NULL means
# "no follow-up scheduled", which is not the same as "due today", so the
# WHERE clause has to exclude it explicitly.
SQL_UPCOMING = """
SELECT m.maintenance_id, m.next_service_date, m.service_type, m.service_date,
       e.equipment_id, e.name AS equipment, e.status
FROM maintenance m
JOIN equipment e ON e.equipment_id = m.equipment_id
WHERE m.next_service_date IS NOT NULL
  AND m.next_service_date <= ?
ORDER BY m.next_service_date ASC;
"""

# Recent activity across two different tables. UNION ALL stacks the two
# result sets; both branches must produce the same number of columns in the
# same order, which is why each one selects a literal 'Repair'/'Service' tag.
SQL_RECENT_ACTIVITY = """
SELECT 'Repair' AS kind, r.repair_id AS record_id, r.repair_date AS on_date,
       r.problem AS summary, r.cost AS cost,
       e.equipment_id, e.name AS equipment
FROM repairs r
JOIN equipment e ON e.equipment_id = r.equipment_id
UNION ALL
SELECT 'Service' AS kind, m.maintenance_id, m.service_date,
       m.service_type, m.cost,
       e.equipment_id, e.name
FROM maintenance m
JOIN equipment e ON e.equipment_id = m.equipment_id
ORDER BY on_date DESC, kind ASC
LIMIT 8;
"""

SQL_STATUS_BREAKDOWN = """
SELECT e.status AS label, COUNT(*) AS n
FROM equipment e
GROUP BY e.status
ORDER BY n DESC;
"""


@app.route("/")
def dashboard():
    counts = query_one(SQL_DASH_COUNTS)
    today = date.today().isoformat()
    horizon = (date.today() + timedelta(days=45)).isoformat()

    upcoming = []
    for row in query_all(SQL_UPCOMING, (horizon,)):
        upcoming.append({**dict(row), "overdue": row["next_service_date"] < today})

    return render_template(
        "dashboard.html",
        counts=counts,
        grand_total=(counts["total_repair_cost"] or 0)
        + (counts["total_maintenance_cost"] or 0),
        upcoming=upcoming,
        overdue_count=sum(1 for u in upcoming if u["overdue"]),
        recent=query_all(SQL_RECENT_ACTIVITY),
        statuses=query_all(SQL_STATUS_BREAKDOWN),
        horizon=horizon,
        sql_snippets={
            "counts": SQL_DASH_COUNTS.strip(),
            "upcoming": SQL_UPCOMING.strip(),
            "recent": SQL_RECENT_ACTIVITY.strip(),
        },
    )


# ---------------------------------------------------------------------------
# 4. EQUIPMENT  — list, search, sort, and full CRUD
# ---------------------------------------------------------------------------
@app.route("/equipment")
def equipment():
    search = request.args.get("search", "").strip()
    etype = request.args.get("equipment_type", "")
    status = request.args.get("status", "")
    sort = request.args.get("sort", "name")
    direction = "DESC" if request.args.get("dir", "asc").lower() == "desc" else "ASC"

    where, params = [], []
    if search:
        # One box searching four columns -- what a farmer actually does.
        # ESCAPE '\' plus like_term() means a literal % or _ in a serial
        # number is searched for literally instead of acting as a wildcard.
        where.append(
            "(e.name LIKE ? ESCAPE '\\' OR e.manufacturer LIKE ? ESCAPE '\\' "
            "OR e.model LIKE ? ESCAPE '\\' OR e.serial_number LIKE ? ESCAPE '\\')"
        )
        params.extend([like_term(search)] * 4)
    if etype in EQUIPMENT_TYPES:
        where.append("e.equipment_type = ?")
        params.append(etype)
    if status in EQUIPMENT_STATUSES:
        where.append("e.status = ?")
        params.append(status)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    order_sql = f"ORDER BY {EQUIPMENT_SORTS.get(sort, 'e.name')} {direction}"

    # Correlated subqueries rather than two LEFT JOINs. Joining both child
    # tables at once would multiply rows (5 repairs x 3 services = 15 rows
    # per machine) and inflate every SUM. See documentation/DEBUGGING.md.
    sql = f"""
SELECT e.*,
       (SELECT COUNT(*)               FROM repairs r     WHERE r.equipment_id = e.equipment_id) AS repair_count,
       (SELECT COALESCE(SUM(r.cost),0) FROM repairs r     WHERE r.equipment_id = e.equipment_id) AS total_repair_cost,
       (SELECT COUNT(*)               FROM maintenance m WHERE m.equipment_id = e.equipment_id) AS maintenance_count,
       (SELECT COALESCE(SUM(m.cost),0) FROM maintenance m WHERE m.equipment_id = e.equipment_id) AS total_maintenance_cost,
       (SELECT MAX(m.service_date)    FROM maintenance m WHERE m.equipment_id = e.equipment_id) AS last_service
FROM equipment e
{where_sql}
{order_sql};
""".strip()

    rows = query_all(sql, params)
    return render_template(
        "equipment.html",
        rows=rows,
        filters={"search": search, "equipment_type": etype, "status": status,
                 "sort": sort, "dir": direction.lower()},
        executed_sql=sql,
        params=params,
        summary={
            "n": len(rows),
            "repair_total": sum(r["total_repair_cost"] for r in rows),
            "maintenance_total": sum(r["total_maintenance_cost"] for r in rows),
        },
    )


@app.route("/equipment/add", methods=["GET", "POST"])
def add_equipment():
    if request.method == "POST":
        cleaned, errors = validate_equipment(request.form)
        if errors:
            for err in errors:
                flash(f"Could not save equipment: {err}.", "error")
            return render_template("equipment_form.html", mode="add", item=request.form)
        cur = execute(
            """INSERT INTO equipment
                 (name, equipment_type, manufacturer, model, year,
                  serial_number, purchase_date, status)
               VALUES (:name, :equipment_type, :manufacturer, :model, :year,
                       :serial_number, :purchase_date, :status);""",
            cleaned,
        )
        flash(f"Registered “{cleaned['name']}”.", "ok")
        return redirect(url_for("equipment_detail", equipment_id=cur.lastrowid))

    return render_template(
        "equipment_form.html",
        mode="add",
        item={"status": "Operational", "equipment_type": "Tractor"},
    )


@app.route("/equipment/<int:equipment_id>")
def equipment_detail(equipment_id):
    item = query_one("SELECT * FROM equipment WHERE equipment_id = ?;", (equipment_id,))
    if item is None:
        flash("That equipment is not in the database.", "error")
        return redirect(url_for("equipment"))

    # LEFT JOIN to mechanics, NOT an inner join: mechanic_id is NULL for a
    # repair the operator did in-house, and an inner join would silently
    # drop those rows from the history and from the totals.
    repairs_sql = """
SELECT r.*, COALESCE(mc.name, 'In-house (no mechanic)') AS mechanic_name, mc.shop
FROM repairs r
LEFT JOIN mechanics mc ON mc.mechanic_id = r.mechanic_id
WHERE r.equipment_id = ?
ORDER BY r.repair_date DESC;
"""
    maintenance_sql = """
SELECT m.*
FROM maintenance m
WHERE m.equipment_id = ?
ORDER BY m.service_date DESC;
"""
    totals_sql = """
SELECT (SELECT COUNT(*)                FROM repairs     WHERE equipment_id = ?) AS repair_count,
       (SELECT COALESCE(SUM(cost), 0)  FROM repairs     WHERE equipment_id = ?) AS total_repair_cost,
       (SELECT COALESCE(AVG(cost), 0)  FROM repairs     WHERE equipment_id = ?) AS avg_repair_cost,
       (SELECT COALESCE(MAX(cost), 0)  FROM repairs     WHERE equipment_id = ?) AS max_repair_cost,
       (SELECT COUNT(*)                FROM maintenance WHERE equipment_id = ?) AS maintenance_count,
       (SELECT COALESCE(SUM(cost), 0)  FROM maintenance WHERE equipment_id = ?) AS total_maintenance_cost,
       (SELECT MAX(service_date)       FROM maintenance WHERE equipment_id = ?) AS last_service,
       (SELECT MIN(next_service_date)  FROM maintenance
         WHERE equipment_id = ? AND next_service_date IS NOT NULL)              AS next_service;
"""
    totals = query_one(totals_sql, (equipment_id,) * 8)
    next_service = totals["next_service"]
    today = date.today().isoformat()

    return render_template(
        "equipment_detail.html",
        item=item,
        repairs=query_all(repairs_sql, (equipment_id,)),
        maintenance=query_all(maintenance_sql, (equipment_id,)),
        totals=totals,
        lifetime_cost=(totals["total_repair_cost"] or 0)
        + (totals["total_maintenance_cost"] or 0),
        next_service=next_service,
        next_overdue=bool(next_service and next_service < today),
        sql_snippets={"repairs": repairs_sql.strip(), "totals": totals_sql.strip()},
    )


@app.route("/equipment/<int:equipment_id>/edit", methods=["GET", "POST"])
def edit_equipment(equipment_id):
    item = query_one("SELECT * FROM equipment WHERE equipment_id = ?;", (equipment_id,))
    if item is None:
        flash("That equipment is not in the database.", "error")
        return redirect(url_for("equipment"))

    if request.method == "POST":
        cleaned, errors = validate_equipment(request.form, existing_id=equipment_id)
        if errors:
            for err in errors:
                flash(f"Could not update equipment: {err}.", "error")
            return render_template(
                "equipment_form.html", mode="edit", item=request.form,
                equipment_id=equipment_id,
            )
        cleaned["equipment_id"] = equipment_id
        execute(
            """UPDATE equipment
                  SET name = :name, equipment_type = :equipment_type,
                      manufacturer = :manufacturer, model = :model, year = :year,
                      serial_number = :serial_number, purchase_date = :purchase_date,
                      status = :status
                WHERE equipment_id = :equipment_id;""",
            cleaned,
        )
        flash(f"Updated “{cleaned['name']}”.", "ok")
        return redirect(url_for("equipment_detail", equipment_id=equipment_id))

    return render_template(
        "equipment_form.html", mode="edit", item=item, equipment_id=equipment_id
    )


@app.route("/equipment/<int:equipment_id>/delete", methods=["POST"])
def delete_equipment(equipment_id):
    item = query_one("SELECT name FROM equipment WHERE equipment_id = ?;", (equipment_id,))
    if item is None:
        flash("That equipment is already gone.", "warn")
        return redirect(url_for("equipment"))
    nr = query_one("SELECT COUNT(*) AS n FROM repairs WHERE equipment_id = ?;",
                   (equipment_id,))["n"]
    nm = query_one("SELECT COUNT(*) AS n FROM maintenance WHERE equipment_id = ?;",
                   (equipment_id,))["n"]
    # Both child foreign keys are ON DELETE CASCADE, so SQLite removes the
    # history for us -- but only because PRAGMA foreign_keys = ON is set.
    execute("DELETE FROM equipment WHERE equipment_id = ?;", (equipment_id,))
    flash(
        f"Deleted “{item['name']}” along with {nr} repair(s) and "
        f"{nm} service record(s) (ON DELETE CASCADE).",
        "ok",
    )
    return redirect(url_for("equipment"))


# ---------------------------------------------------------------------------
# 5. REPAIRS  — list, filter, sort, full CRUD
# ---------------------------------------------------------------------------
@app.route("/repairs")
def repairs():
    equipment_id = request.args.get("equipment_id", "")
    mechanic_id = request.args.get("mechanic_id", "")
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    min_cost = request.args.get("min_cost", "").strip()
    search = request.args.get("search", "").strip()
    sort = request.args.get("sort", "date")
    direction = "ASC" if request.args.get("dir", "desc").lower() == "asc" else "DESC"

    where, params = [], []
    if equipment_id:
        where.append("r.equipment_id = ?")
        params.append(equipment_id)
    if mechanic_id == "none":
        where.append("r.mechanic_id IS NULL")       # in-house repairs
    elif mechanic_id:
        where.append("r.mechanic_id = ?")
        params.append(mechanic_id)
    if DATE_RE.match(date_from or ""):
        where.append("r.repair_date >= ?")
        params.append(date_from)
    if DATE_RE.match(date_to or ""):
        where.append("r.repair_date <= ?")
        params.append(date_to)
    if min_cost:
        try:
            value = float(min_cost)
            where.append("r.cost >= ?")
            params.append(value)
        except ValueError:
            flash("Minimum cost ignored — it was not a number.", "warn")
    if search:
        where.append(
            "(r.problem LIKE ? ESCAPE '\\' "
            "OR r.repair_description LIKE ? ESCAPE '\\')"
        )
        params.extend([like_term(search)] * 2)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    order_sql = f"ORDER BY {REPAIR_SORTS.get(sort, 'r.repair_date')} {direction}"

    sql = f"""
SELECT r.*, e.name AS equipment, e.equipment_type,
       COALESCE(mc.name, 'In-house (no mechanic)') AS mechanic_name
FROM repairs r
JOIN equipment e       ON e.equipment_id = r.equipment_id
LEFT JOIN mechanics mc ON mc.mechanic_id = r.mechanic_id
{where_sql}
{order_sql};
""".strip()
    rows = query_all(sql, params)

    summary_sql = f"""
SELECT COUNT(*) AS n, COALESCE(SUM(r.cost),0) AS total,
       COALESCE(AVG(r.cost),0) AS average,
       COALESCE(MIN(r.cost),0) AS smallest, COALESCE(MAX(r.cost),0) AS largest
FROM repairs r
JOIN equipment e       ON e.equipment_id = r.equipment_id
LEFT JOIN mechanics mc ON mc.mechanic_id = r.mechanic_id
{where_sql};
""".strip()
    summary = query_one(summary_sql, params)

    return render_template(
        "repairs.html",
        rows=rows,
        summary=summary,
        equipment_list=all_equipment(),
        mechanics=all_mechanics(),
        filters={"equipment_id": equipment_id, "mechanic_id": mechanic_id,
                 "date_from": date_from, "date_to": date_to, "min_cost": min_cost,
                 "search": search, "sort": sort, "dir": direction.lower()},
        executed_sql=sql,
        params=params,
    )


@app.route("/repairs/add", methods=["GET", "POST"])
def add_repair():
    if request.method == "POST":
        cleaned, errors = validate_repair(request.form)
        if errors:
            for err in errors:
                flash(f"Could not save repair: {err}.", "error")
            return render_template(
                "repair_form.html", mode="add", item=request.form,
                equipment_list=all_equipment(), mechanics=all_mechanics(),
            )
        execute(
            """INSERT INTO repairs
                 (equipment_id, mechanic_id, repair_date, problem,
                  repair_description, cost, notes)
               VALUES (:equipment_id, :mechanic_id, :repair_date, :problem,
                       :repair_description, :cost, :notes);""",
            cleaned,
        )
        flash(f"Logged repair: “{cleaned['problem']}”.", "ok")
        return redirect(url_for("equipment_detail", equipment_id=cleaned["equipment_id"]))

    return render_template(
        "repair_form.html",
        mode="add",
        item={"repair_date": date.today().isoformat(),
              "equipment_id": request.args.get("equipment_id", "")},
        equipment_list=all_equipment(),
        mechanics=all_mechanics(),
    )


@app.route("/repairs/<int:repair_id>/edit", methods=["GET", "POST"])
def edit_repair(repair_id):
    item = query_one("SELECT * FROM repairs WHERE repair_id = ?;", (repair_id,))
    if item is None:
        flash("That repair record no longer exists.", "error")
        return redirect(url_for("repairs"))

    if request.method == "POST":
        cleaned, errors = validate_repair(request.form)
        if errors:
            for err in errors:
                flash(f"Could not update repair: {err}.", "error")
            return render_template(
                "repair_form.html", mode="edit", item=request.form, repair_id=repair_id,
                equipment_list=all_equipment(), mechanics=all_mechanics(),
            )
        cleaned["repair_id"] = repair_id
        execute(
            """UPDATE repairs
                  SET equipment_id = :equipment_id, mechanic_id = :mechanic_id,
                      repair_date = :repair_date, problem = :problem,
                      repair_description = :repair_description,
                      cost = :cost, notes = :notes
                WHERE repair_id = :repair_id;""",
            cleaned,
        )
        flash(f"Updated repair #{repair_id}.", "ok")
        return redirect(url_for("equipment_detail", equipment_id=cleaned["equipment_id"]))

    return render_template(
        "repair_form.html", mode="edit", item=item, repair_id=repair_id,
        equipment_list=all_equipment(), mechanics=all_mechanics(),
    )


@app.route("/repairs/<int:repair_id>/delete", methods=["POST"])
def delete_repair(repair_id):
    row = query_one("SELECT equipment_id FROM repairs WHERE repair_id = ?;", (repair_id,))
    cur = execute("DELETE FROM repairs WHERE repair_id = ?;", (repair_id,))
    if cur.rowcount:
        flash(f"Deleted repair #{repair_id} from the database.", "ok")
    else:
        flash(f"No repair with id {repair_id} — nothing deleted.", "warn")
    return redirect(_safe_back(url_for("edit_repair", repair_id=repair_id),
                               url_for("repairs")))


# ---------------------------------------------------------------------------
# 6. MAINTENANCE  — list, filter, sort, full CRUD
# ---------------------------------------------------------------------------
@app.route("/maintenance")
def maintenance():
    equipment_id = request.args.get("equipment_id", "")
    service_type = request.args.get("service_type", "")
    due = request.args.get("due", "")
    sort = request.args.get("sort", "date")
    direction = "ASC" if request.args.get("dir", "desc").lower() == "asc" else "DESC"

    where, params = [], []
    if equipment_id:
        where.append("m.equipment_id = ?")
        params.append(equipment_id)
    if service_type in SERVICE_TYPES:
        where.append("m.service_type = ?")
        params.append(service_type)
    if due == "overdue":
        where.append("m.next_service_date IS NOT NULL AND m.next_service_date < ?")
        params.append(date.today().isoformat())
    elif due == "scheduled":
        where.append("m.next_service_date IS NOT NULL AND m.next_service_date >= ?")
        params.append(date.today().isoformat())
    elif due == "none":
        where.append("m.next_service_date IS NULL")

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    order_sql = f"ORDER BY {MAINTENANCE_SORTS.get(sort, 'm.service_date')} {direction}"

    sql = f"""
SELECT m.*, e.name AS equipment, e.equipment_type
FROM maintenance m
JOIN equipment e ON e.equipment_id = m.equipment_id
{where_sql}
{order_sql};
""".strip()
    rows = query_all(sql, params)

    summary_sql = f"""
SELECT COUNT(*) AS n, COALESCE(SUM(m.cost),0) AS total,
       COALESCE(AVG(m.cost),0) AS average,
       COALESCE(MIN(m.cost),0) AS smallest, COALESCE(MAX(m.cost),0) AS largest
FROM maintenance m
JOIN equipment e ON e.equipment_id = m.equipment_id
{where_sql};
""".strip()

    today = date.today().isoformat()
    return render_template(
        "maintenance.html",
        rows=rows,
        summary=query_one(summary_sql, params),
        equipment_list=all_equipment(),
        today=today,
        filters={"equipment_id": equipment_id, "service_type": service_type,
                 "due": due, "sort": sort, "dir": direction.lower()},
        executed_sql=sql,
        params=params,
    )


@app.route("/maintenance/add", methods=["GET", "POST"])
def add_maintenance():
    if request.method == "POST":
        cleaned, errors = validate_maintenance(request.form)
        if errors:
            for err in errors:
                flash(f"Could not save service record: {err}.", "error")
            return render_template(
                "maintenance_form.html", mode="add", item=request.form,
                equipment_list=all_equipment(),
            )
        execute(
            """INSERT INTO maintenance
                 (equipment_id, service_date, service_type, description,
                  cost, next_service_date, notes)
               VALUES (:equipment_id, :service_date, :service_type, :description,
                       :cost, :next_service_date, :notes);""",
            cleaned,
        )
        flash(f"Logged service: {cleaned['service_type']}.", "ok")
        return redirect(url_for("equipment_detail", equipment_id=cleaned["equipment_id"]))

    return render_template(
        "maintenance_form.html",
        mode="add",
        item={"service_date": date.today().isoformat(),
              "service_type": "Oil Change",
              "equipment_id": request.args.get("equipment_id", "")},
        equipment_list=all_equipment(),
    )


@app.route("/maintenance/<int:maintenance_id>/edit", methods=["GET", "POST"])
def edit_maintenance(maintenance_id):
    item = query_one(
        "SELECT * FROM maintenance WHERE maintenance_id = ?;", (maintenance_id,)
    )
    if item is None:
        flash("That service record no longer exists.", "error")
        return redirect(url_for("maintenance"))

    if request.method == "POST":
        cleaned, errors = validate_maintenance(request.form)
        if errors:
            for err in errors:
                flash(f"Could not update service record: {err}.", "error")
            return render_template(
                "maintenance_form.html", mode="edit", item=request.form,
                maintenance_id=maintenance_id, equipment_list=all_equipment(),
            )
        cleaned["maintenance_id"] = maintenance_id
        execute(
            """UPDATE maintenance
                  SET equipment_id = :equipment_id, service_date = :service_date,
                      service_type = :service_type, description = :description,
                      cost = :cost, next_service_date = :next_service_date,
                      notes = :notes
                WHERE maintenance_id = :maintenance_id;""",
            cleaned,
        )
        flash(f"Updated service record #{maintenance_id}.", "ok")
        return redirect(url_for("equipment_detail", equipment_id=cleaned["equipment_id"]))

    return render_template(
        "maintenance_form.html", mode="edit", item=item,
        maintenance_id=maintenance_id, equipment_list=all_equipment(),
    )


@app.route("/maintenance/<int:maintenance_id>/delete", methods=["POST"])
def delete_maintenance(maintenance_id):
    cur = execute(
        "DELETE FROM maintenance WHERE maintenance_id = ?;", (maintenance_id,)
    )
    if cur.rowcount:
        flash(f"Deleted service record #{maintenance_id} from the database.", "ok")
    else:
        flash(f"No service record with id {maintenance_id} — nothing deleted.", "warn")
    return redirect(
        _safe_back(url_for("edit_maintenance", maintenance_id=maintenance_id),
                   url_for("maintenance"))
    )


def _safe_back(dead_url, fallback):
    """Return to the referring page, unless that page is the record we deleted.

    Sending the user back to request.referrer preserves their filters. But if
    the delete came from that record's own edit page, the referrer is now a
    dead URL and the edit view would flash a contradictory "no longer exists"
    message on top of the success message.
    """
    back = request.referrer or ""
    if not back or dead_url in back:
        return fallback
    return back


# ---------------------------------------------------------------------------
# 7. MECHANICS  — small lookup table, kept honest with add/list/delete
# ---------------------------------------------------------------------------
SQL_MECHANIC_ROLLUP = """
SELECT mc.mechanic_id, mc.name, mc.shop, mc.phone, mc.specialty,
       COUNT(r.repair_id)             AS repair_count,
       COALESCE(SUM(r.cost), 0)       AS total_billed,
       COALESCE(AVG(r.cost), 0)       AS average_repair,
       MAX(r.repair_date)             AS last_seen
FROM mechanics mc
LEFT JOIN repairs r ON r.mechanic_id = mc.mechanic_id
GROUP BY mc.mechanic_id, mc.name, mc.shop, mc.phone, mc.specialty
ORDER BY total_billed DESC;
"""


@app.route("/mechanics", methods=["GET", "POST"])
def mechanics():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        if not name:
            flash("Could not add mechanic: name is required.", "error")
        else:
            execute(
                "INSERT INTO mechanics (name, shop, phone, specialty) "
                "VALUES (?, ?, ?, ?);",
                (
                    name,
                    (request.form.get("shop") or "").strip() or None,
                    (request.form.get("phone") or "").strip() or None,
                    (request.form.get("specialty") or "").strip() or None,
                ),
            )
            flash(f"Added mechanic {name}.", "ok")
        return redirect(url_for("mechanics"))

    inhouse = query_one(
        "SELECT COUNT(*) AS n, COALESCE(SUM(cost),0) AS total "
        "FROM repairs WHERE mechanic_id IS NULL;"
    )
    return render_template(
        "mechanics.html",
        rows=query_all(SQL_MECHANIC_ROLLUP),
        inhouse=inhouse,
        sql=SQL_MECHANIC_ROLLUP.strip(),
    )


@app.route("/mechanics/<int:mechanic_id>/delete", methods=["POST"])
def delete_mechanic(mechanic_id):
    row = query_one("SELECT name FROM mechanics WHERE mechanic_id = ?;", (mechanic_id,))
    if row is None:
        flash("That mechanic is already gone.", "warn")
        return redirect(url_for("mechanics"))
    n = query_one("SELECT COUNT(*) AS n FROM repairs WHERE mechanic_id = ?;",
                  (mechanic_id,))["n"]
    # repairs.mechanic_id is ON DELETE SET NULL, not CASCADE: the repair still
    # happened and still cost money, so the record survives with no mechanic.
    execute("DELETE FROM mechanics WHERE mechanic_id = ?;", (mechanic_id,))
    flash(
        f"Removed {row['name']}. {n} repair record(s) kept, now showing as "
        f"in-house (ON DELETE SET NULL).",
        "ok",
    )
    return redirect(url_for("mechanics"))


# ---------------------------------------------------------------------------
# 8. REPORTS  — JOIN, GROUP BY, HAVING, aggregate functions
# ---------------------------------------------------------------------------
REPORTS = {
    "cost_by_equipment": (
        "Lifetime cost by machine",
        "Which machine is costing the most to keep running? Repairs and services "
        "live in two different tables, so each total is a correlated subquery — "
        "joining both child tables at once would multiply the rows and inflate "
        "every sum.",
        """
SELECT e.name AS label,
       (SELECT COUNT(*)                FROM repairs r     WHERE r.equipment_id = e.equipment_id) AS repair_n,
       (SELECT COALESCE(SUM(r.cost),0) FROM repairs r     WHERE r.equipment_id = e.equipment_id) AS repair_total,
       (SELECT COUNT(*)                FROM maintenance m WHERE m.equipment_id = e.equipment_id) AS service_n,
       (SELECT COALESCE(SUM(m.cost),0) FROM maintenance m WHERE m.equipment_id = e.equipment_id) AS service_total,
       (SELECT COALESCE(SUM(r.cost),0) FROM repairs r     WHERE r.equipment_id = e.equipment_id)
     + (SELECT COALESCE(SUM(m.cost),0) FROM maintenance m WHERE m.equipment_id = e.equipment_id) AS total
FROM equipment e
ORDER BY total DESC;
""",
    ),
}

SQL_REPAIRS_BY_EQUIPMENT = """
SELECT e.name AS label,
       COUNT(r.repair_id)       AS n,
       COALESCE(SUM(r.cost), 0) AS total,
       COALESCE(AVG(r.cost), 0) AS average,
       COALESCE(MIN(r.cost), 0) AS smallest,
       COALESCE(MAX(r.cost), 0) AS largest
FROM equipment e
LEFT JOIN repairs r ON r.equipment_id = e.equipment_id
GROUP BY e.equipment_id, e.name
ORDER BY total DESC;
"""

SQL_MAINTENANCE_BY_EQUIPMENT = """
SELECT e.name AS label,
       COUNT(m.maintenance_id)  AS n,
       COALESCE(SUM(m.cost), 0) AS total,
       COALESCE(AVG(m.cost), 0) AS average,
       COALESCE(MIN(m.cost), 0) AS smallest,
       COALESCE(MAX(m.cost), 0) AS largest
FROM equipment e
LEFT JOIN maintenance m ON m.equipment_id = e.equipment_id
GROUP BY e.equipment_id, e.name
ORDER BY total DESC;
"""

SQL_BY_SERVICE_TYPE = """
SELECT m.service_type AS label,
       COUNT(*)      AS n,
       SUM(m.cost)   AS total,
       AVG(m.cost)   AS average,
       MIN(m.cost)   AS smallest,
       MAX(m.cost)   AS largest
FROM maintenance m
GROUP BY m.service_type
ORDER BY total DESC;
"""

SQL_BY_MECHANIC = """
SELECT COALESCE(mc.name, 'In-house (no mechanic)') AS label,
       COUNT(*)     AS n,
       SUM(r.cost)  AS total,
       AVG(r.cost)  AS average,
       MIN(r.cost)  AS smallest,
       MAX(r.cost)  AS largest
FROM repairs r
LEFT JOIN mechanics mc ON mc.mechanic_id = r.mechanic_id
GROUP BY mc.mechanic_id, label
ORDER BY total DESC;
"""

SQL_BY_MONTH = """
SELECT strftime('%Y-%m', r.repair_date) AS label,
       COUNT(*)     AS n,
       SUM(r.cost)  AS total,
       AVG(r.cost)  AS average,
       MIN(r.cost)  AS smallest,
       MAX(r.cost)  AS largest
FROM repairs r
GROUP BY label
ORDER BY label;
"""

SQL_PROBLEM_MACHINES = """
SELECT e.name AS label,
       COUNT(*)     AS n,
       SUM(r.cost)  AS total,
       AVG(r.cost)  AS average,
       MIN(r.cost)  AS smallest,
       MAX(r.cost)  AS largest
FROM repairs r
JOIN equipment e ON e.equipment_id = r.equipment_id
GROUP BY e.equipment_id, e.name
HAVING COUNT(*) >= 2 AND SUM(r.cost) > 500
ORDER BY total DESC;
"""

SQL_RECENT_REPAIRS = """
SELECT e.name AS equipment, r.repair_date, r.problem, r.cost,
       COALESCE(mc.name, 'In-house') AS mechanic
FROM equipment e
JOIN repairs r         ON e.equipment_id = r.equipment_id
LEFT JOIN mechanics mc ON mc.mechanic_id = r.mechanic_id
ORDER BY r.repair_date DESC
LIMIT 5;
"""

SQL_SERVICE_DUE = """
SELECT e.name AS equipment, e.status, m.service_type, m.service_date,
       m.next_service_date
FROM maintenance m
JOIN equipment e ON e.equipment_id = m.equipment_id
WHERE m.next_service_date IS NOT NULL
ORDER BY m.next_service_date ASC
LIMIT 10;
"""


@app.route("/reports")
def reports():
    title, blurb, sql = REPORTS["cost_by_equipment"]
    lifetime = query_all(sql)

    grouped = {
        "repairs_by_equipment": {
            "title": "Repair count and cost by machine",
            "blurb": "LEFT JOIN keeps a machine with no repairs yet — an inner join "
                     "would drop it, and a report of $0.00 is not the same as a "
                     "machine that is missing from the list.",
            "sql": SQL_REPAIRS_BY_EQUIPMENT.strip(),
            "rows": query_all(SQL_REPAIRS_BY_EQUIPMENT),
        },
        "maintenance_by_equipment": {
            "title": "Service count and cost by machine",
            "blurb": "The same shape against the maintenance table. Compare it with "
                     "the panel above: high service cost is planned spending, high "
                     "repair cost is not.",
            "sql": SQL_MAINTENANCE_BY_EQUIPMENT.strip(),
            "rows": query_all(SQL_MAINTENANCE_BY_EQUIPMENT),
        },
        "by_service_type": {
            "title": "Spending by service type",
            "blurb": "Where the routine money goes. A plain GROUP BY on one column, "
                     "no join needed.",
            "sql": SQL_BY_SERVICE_TYPE.strip(),
            "rows": query_all(SQL_BY_SERVICE_TYPE),
        },
        "by_mechanic": {
            "title": "Repair spending by mechanic",
            "blurb": "LEFT JOIN plus COALESCE so that in-house repairs — the ones "
                     "with a NULL mechanic_id — are grouped and reported instead of "
                     "vanishing.",
            "sql": SQL_BY_MECHANIC.strip(),
            "rows": query_all(SQL_BY_MECHANIC),
        },
        "by_month": {
            "title": "Repair spending by month",
            "blurb": "SQLite has no DATE type, so dates are ISO text and "
                     "strftime('%Y-%m', ...) extracts the month to group on.",
            "sql": SQL_BY_MONTH.strip(),
            "rows": query_all(SQL_BY_MONTH),
        },
        "problem_machines": {
            "title": "Problem machines (HAVING)",
            "blurb": "WHERE filters individual rows before grouping; HAVING filters "
                     "the groups afterwards. This is every machine with at least two "
                     "repairs AND more than $500 of repair spending.",
            "sql": SQL_PROBLEM_MACHINES.strip(),
            "rows": query_all(SQL_PROBLEM_MACHINES),
        },
    }
    for panel in grouped.values():
        panel["top"] = max([r["total"] for r in panel["rows"]] or [0]) or 1

    today = date.today().isoformat()
    due = [
        {**dict(r), "overdue": r["next_service_date"] < today}
        for r in query_all(SQL_SERVICE_DUE)
    ]

    return render_template(
        "reports.html",
        lifetime={"title": title, "blurb": blurb, "sql": sql.strip(),
                  "rows": lifetime,
                  "top": max([r["total"] for r in lifetime] or [0]) or 1},
        grouped=grouped,
        recent_repairs=query_all(SQL_RECENT_REPAIRS),
        recent_sql=SQL_RECENT_REPAIRS.strip(),
        due=due,
        due_sql=SQL_SERVICE_DUE.strip(),
    )


# ---------------------------------------------------------------------------
# 9. CSV IMPORT  (equipment)
# ---------------------------------------------------------------------------
CSV_COLUMNS = [
    "name", "equipment_type", "manufacturer", "model",
    "year", "serial_number", "purchase_date", "status",
]


@app.route("/import", methods=["GET", "POST"])
def import_csv():
    result = None
    if request.method == "POST":
        upload = request.files.get("csv_file")
        if not upload or not upload.filename:
            flash("Choose a .csv file first.", "error")
            return redirect(url_for("import_csv"))
        if not upload.filename.lower().endswith(".csv"):
            flash("That file is not a .csv.", "error")
            return redirect(url_for("import_csv"))

        # utf-8-sig strips the byte-order mark Excel writes at the start of a
        # CSV. Without it the first header would be '﻿name', not 'name'.
        text = upload.stream.read().decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(io.StringIO(text))

        missing = [c for c in CSV_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            flash(f"CSV is missing required column(s): {', '.join(missing)}.", "error")
            return redirect(url_for("import_csv"))

        accepted, rejected = [], []
        seen_serials = set()
        for line_no, raw in enumerate(reader, start=2):   # line 1 is the header
            cleaned, errors = validate_equipment(raw)
            # Duplicates *within the same file* are not caught by the database
            # check, because none of the rows have been inserted yet.
            serial = cleaned["serial_number"]
            if serial and serial in seen_serials:
                errors.append(f"serial number '{serial}' appears twice in this file")
            if errors:
                rejected.append({"line": line_no, "raw": raw, "errors": errors})
            else:
                if serial:
                    seen_serials.add(serial)
                accepted.append(cleaned)

        if accepted:
            db = get_db()
            db.executemany(
                """INSERT INTO equipment
                     (name, equipment_type, manufacturer, model, year,
                      serial_number, purchase_date, status)
                   VALUES (:name, :equipment_type, :manufacturer, :model, :year,
                           :serial_number, :purchase_date, :status);""",
                accepted,
            )
            db.commit()

        result = {"accepted": len(accepted), "rejected": rejected,
                  "total": len(accepted) + len(rejected)}
        flash(
            f"Imported {len(accepted)} of {result['total']} row(s); "
            f"{len(rejected)} rejected.",
            "ok" if not rejected else "warn",
        )

    return render_template("import.html", result=result, columns=CSV_COLUMNS)


# ---------------------------------------------------------------------------
# 10. SCHEMA INSPECTION
# ---------------------------------------------------------------------------
@app.route("/schema")
def schema():
    db = get_db()
    tables = []
    for (name,) in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name;"
    ).fetchall():
        tables.append({
            "name": name,
            "columns": db.execute(f"PRAGMA table_info({name});").fetchall(),
            "foreign_keys": db.execute(f"PRAGMA foreign_key_list({name});").fetchall(),
            "indexes": db.execute(f"PRAGMA index_list({name});").fetchall(),
            "row_count": db.execute(f"SELECT COUNT(*) FROM {name};").fetchone()[0],
            "ddl": db.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name = ?;",
                (name,),
            ).fetchone()[0],
        })
    return render_template(
        "schema.html",
        tables=tables,
        fk_on=bool(db.execute("PRAGMA foreign_keys;").fetchone()[0]),
        fk_problems=db.execute("PRAGMA foreign_key_check;").fetchall(),
        sqlite_version=sqlite3.sqlite_version,
        db_path=DB_PATH,
        db_size_kb=round(os.path.getsize(DB_PATH) / 1024, 1)
        if os.path.exists(DB_PATH) else 0,
    )


# ---------------------------------------------------------------------------
# 11. ABOUT PROJECT
# ---------------------------------------------------------------------------
@app.route("/about")
def about():
    counts = query_one(
        """SELECT (SELECT COUNT(*) FROM equipment)   AS equipment,
                  (SELECT COUNT(*) FROM mechanics)   AS mechanics,
                  (SELECT COUNT(*) FROM repairs)     AS repairs,
                  (SELECT COUNT(*) FROM maintenance) AS maintenance;"""
    )
    return render_template("about.html", counts=counts,
                           sqlite_version=sqlite3.sqlite_version)


@app.errorhandler(404)
def not_found(_e):
    return render_template("error.html", code=404,
                           message="That page does not exist."), 404


@app.errorhandler(500)
def server_error(_e):
    return render_template("error.html", code=500,
                           message="Something went wrong on the server."), 500


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        raise SystemExit(
            "database/farmfix.db not found.\n"
            "Create it first with:  python database/init_db.py"
        )
    app.run(debug=True, host="127.0.0.1", port=5000)
