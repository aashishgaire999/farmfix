"""
FarmFix automated test suite
COMP 368 Database Systems, Project 1
Team: Ayush Gaire, Ashish Gaire, AJ Rayamajhi

Run from the project root:
    python -m pytest tests/ -v

Every test builds a fresh throwaway database in a temporary directory from
database/schema.sql and database/sample_data.sql, so running the tests never
touches database/farmfix.db. That is why every test can assume the same
starting state: 5 machines, 3 mechanics, 10 repairs, 11 service records.

The numbered tests correspond one-for-one to the table in
documentation/TESTING.md.
"""

import io
import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as farmfix  # noqa: E402

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(PROJECT_ROOT, "database", "schema.sql")
SAMPLE = os.path.join(PROJECT_ROOT, "database", "sample_data.sql")

# Seeded totals, verified by hand against database/sample_data.sql.
SEED_EQUIPMENT = 5
SEED_MECHANICS = 3
SEED_REPAIRS = 10
SEED_MAINTENANCE = 11
SEED_REPAIR_COST = 4381.20
SEED_MAINTENANCE_COST = 2014.75


@pytest.fixture()
def db_path(tmp_path):
    """A fresh copy of the real schema + sample data, in a temp directory."""
    path = str(tmp_path / "test.db")
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON;")
    with open(SCHEMA, encoding="utf-8") as fh:
        conn.executescript(fh.read())
    with open(SAMPLE, encoding="utf-8") as fh:
        conn.executescript(fh.read())
    conn.commit()
    conn.close()
    return path


@pytest.fixture()
def client(db_path, monkeypatch):
    monkeypatch.setattr(farmfix, "DB_PATH", db_path)
    farmfix.app.config["TESTING"] = True
    with farmfix.app.test_client() as c:
        yield c


@pytest.fixture()
def raw(db_path):
    """A direct SQLite connection, for asserting on the database itself."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    yield conn
    conn.close()


def count(conn, table):
    return conn.execute(f"SELECT COUNT(*) AS n FROM {table};").fetchone()["n"]


# ===========================================================================
# TEST 1 — Add Equipment (CREATE)
# ===========================================================================
def test_01_add_equipment(client, raw):
    before = count(raw, "equipment")

    response = client.post(
        "/equipment/add",
        data={
            "name": "TEST 1 - Fendt 724 Vario",
            "equipment_type": "Tractor",
            "manufacturer": "Fendt",
            "model": "724 Vario",
            "year": "2023",
            "serial_number": "TEST1SERIAL0001",
            "purchase_date": "2023-04-11",
            "status": "Operational",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert count(raw, "equipment") == before + 1

    row = raw.execute(
        "SELECT * FROM equipment WHERE serial_number = 'TEST1SERIAL0001';"
    ).fetchone()
    assert row is not None
    assert row["name"] == "TEST 1 - Fendt 724 Vario"
    assert row["manufacturer"] == "Fendt"
    assert row["year"] == 2023
    assert row["equipment_type"] == "Tractor"
    # ...and it is visible through the web interface
    assert b"TEST 1 - Fendt 724 Vario" in client.get("/equipment").data


@pytest.mark.parametrize(
    "field,value,expected_fragment",
    [
        ("name", "", "name is required"),
        ("manufacturer", "", "manufacturer is required"),
        ("equipment_type", "Spaceship", "equipment type"),
        ("status", "Broken Down", "status"),
        ("year", "nineteen", "not a whole number"),
        ("year", "1750", "between 1900 and 2100"),
        ("purchase_date", "04/11/2023", "YYYY-MM-DD"),
        ("serial_number", "1LV5075EKKY123456", "already registered"),
    ],
)
def test_01b_invalid_equipment_rejected(client, raw, field, value, expected_fragment):
    payload = {
        "name": "TEST 1b - should not be saved",
        "equipment_type": "Tractor",
        "manufacturer": "Fendt",
        "model": "724",
        "year": "2023",
        "serial_number": "TEST1BSERIAL999",
        "purchase_date": "2023-04-11",
        "status": "Operational",
    }
    payload[field] = value
    before = count(raw, "equipment")

    response = client.post("/equipment/add", data=payload, follow_redirects=True)

    assert response.status_code == 200
    assert b"Could not save equipment" in response.data
    assert expected_fragment.encode() in response.data
    assert count(raw, "equipment") == before, f"a bad {field} reached the database"


# ===========================================================================
# TEST 2 — Add Repair against a valid foreign key
# ===========================================================================
def test_02_add_repair(client, raw):
    before = count(raw, "repairs")

    response = client.post(
        "/repairs/add",
        data={
            "equipment_id": "2",           # Kubota L3902
            "mechanic_id": "1",            # Dale Hutchins
            "repair_date": "2026-09-03",
            "problem": "TEST 2 - PTO shaft guard cracked",
            "repair_description": "Replaced guard and both retaining clips.",
            "cost": "212.50",
            "notes": "Test record.",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert count(raw, "repairs") == before + 1

    row = raw.execute(
        "SELECT * FROM repairs WHERE problem = 'TEST 2 - PTO shaft guard cracked';"
    ).fetchone()
    assert row is not None
    assert row["equipment_id"] == 2, "foreign key was not stored correctly"
    assert row["mechanic_id"] == 1
    assert row["cost"] == 212.50

    # It must appear in that machine's history page, and nowhere else.
    detail = client.get("/equipment/2").data
    assert b"TEST 2 - PTO shaft guard cracked" in detail
    assert b"TEST 2 - PTO shaft guard cracked" not in client.get("/equipment/1").data


def test_02b_repair_without_mechanic_is_allowed(client, raw):
    """Multiplicity 0..1: an in-house repair has no mechanic on record."""
    response = client.post(
        "/repairs/add",
        data={
            "equipment_id": "1",
            "mechanic_id": "",             # deliberately blank
            "repair_date": "2026-09-03",
            "problem": "TEST 2b - in-house fix",
            "cost": "12.00",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    row = raw.execute(
        "SELECT * FROM repairs WHERE problem = 'TEST 2b - in-house fix';"
    ).fetchone()
    assert row is not None
    assert row["mechanic_id"] is None
    # ...and the LEFT JOIN still shows it, labelled as in-house
    assert b"TEST 2b - in-house fix" in client.get("/equipment/1").data
    assert b"In-house" in client.get("/repairs").data


@pytest.mark.parametrize(
    "field,value,expected_fragment",
    [
        ("equipment_id", "", "equipment is required"),
        ("equipment_id", "9999", "no equipment with id 9999"),
        ("mechanic_id", "9999", "no mechanic with id 9999"),
        ("problem", "", "problem description is required"),
        ("repair_date", "09/03/2026", "YYYY-MM-DD"),
        ("cost", "-40", "cost cannot be negative"),
        ("cost", "free", "is not a number"),
    ],
)
def test_02c_invalid_repair_rejected(client, raw, field, value, expected_fragment):
    payload = {
        "equipment_id": "1",
        "mechanic_id": "",
        "repair_date": "2026-09-03",
        "problem": "TEST 2c - should not be saved",
        "repair_description": "",
        "cost": "50.00",
        "notes": "",
    }
    payload[field] = value
    before = count(raw, "repairs")

    response = client.post("/repairs/add", data=payload, follow_redirects=True)

    assert response.status_code == 200
    assert b"Could not save repair" in response.data
    assert expected_fragment.encode() in response.data
    assert count(raw, "repairs") == before, f"a bad {field} reached the database"


# ===========================================================================
# TEST 3 — SQL report: JOIN + GROUP BY + SUM must be arithmetically correct
# ===========================================================================
def test_03_repair_cost_report_is_correct(client, raw):
    """The grouped report must equal the same totals computed row by row."""
    grouped = {
        r["name"]: round(r["total"], 2)
        for r in raw.execute(
            """SELECT e.name, COALESCE(SUM(r.cost), 0) AS total
               FROM equipment e
               LEFT JOIN repairs r ON r.equipment_id = e.equipment_id
               GROUP BY e.equipment_id, e.name;"""
        ).fetchall()
    }

    manual = {}
    for row in raw.execute(
        """SELECT e.name, r.cost FROM repairs r
           JOIN equipment e ON e.equipment_id = r.equipment_id;"""
    ).fetchall():
        manual[row["name"]] = round(manual.get(row["name"], 0) + row["cost"], 2)

    for name, total in manual.items():
        assert grouped[name] == total, f"grouped total wrong for {name}"

    # the grand total must reconcile with the whole table
    assert round(sum(grouped.values()), 2) == SEED_REPAIR_COST

    # LEFT JOIN keeps a machine that has never been repaired
    raw.execute(
        "INSERT INTO equipment (name, manufacturer) VALUES ('Brand New', 'Kubota');"
    )
    raw.commit()
    rows = raw.execute(
        """SELECT e.name, COALESCE(SUM(r.cost), 0) AS total
           FROM equipment e
           LEFT JOIN repairs r ON r.equipment_id = e.equipment_id
           GROUP BY e.equipment_id, e.name;"""
    ).fetchall()
    assert any(r["name"] == "Brand New" and r["total"] == 0 for r in rows)

    assert client.get("/reports").status_code == 200


def test_03b_lifetime_cost_is_not_inflated_by_a_double_join(client, raw):
    """Regression test for the bug in documentation/DEBUGGING.md.

    Joining BOTH child tables in one query multiplies the rows: a machine with
    3 repairs and 3 services produces 9 rows, and SUM(cost) comes out three
    times too high. The application uses correlated subqueries instead. This
    test pins the correct numbers AND demonstrates that the naive version is
    wrong, so nobody "simplifies" it back.
    """
    # --- the correct answer, computed one table at a time -------------------
    truth = {}
    for e in raw.execute("SELECT equipment_id, name FROM equipment;"):
        r = raw.execute(
            "SELECT COALESCE(SUM(cost),0) AS t FROM repairs WHERE equipment_id = ?;",
            (e["equipment_id"],),
        ).fetchone()["t"]
        m = raw.execute(
            "SELECT COALESCE(SUM(cost),0) AS t FROM maintenance WHERE equipment_id = ?;",
            (e["equipment_id"],),
        ).fetchone()["t"]
        truth[e["name"]] = round(r + m, 2)

    # --- what the application actually runs ---------------------------------
    app_sql = farmfix.REPORTS["cost_by_equipment"][2]
    produced = {r["label"]: round(r["total"], 2) for r in raw.execute(app_sql)}
    assert produced == truth

    # --- what the "obvious" version would have produced ----------------------
    naive = raw.execute(
        """SELECT e.name, COALESCE(SUM(r.cost), 0) AS repair_total
           FROM equipment e
           LEFT JOIN repairs r     ON r.equipment_id = e.equipment_id
           LEFT JOIN maintenance m ON m.equipment_id = e.equipment_id
           GROUP BY e.equipment_id, e.name;"""
    ).fetchall()
    naive_5075e = next(r["repair_total"] for r in naive if r["name"] == "John Deere 5075E")
    true_5075e = raw.execute(
        "SELECT SUM(cost) AS t FROM repairs WHERE equipment_id = 1;"
    ).fetchone()["t"]
    assert round(naive_5075e, 2) == 2982.90
    assert round(true_5075e, 2) == 994.30
    assert naive_5075e > true_5075e, "the double join should over-count -- it did not"


# ===========================================================================
# TEST 4 — Add Maintenance, and the nullable next_service_date
# ===========================================================================
def test_04_add_maintenance(client, raw):
    before = count(raw, "maintenance")

    response = client.post(
        "/maintenance/add",
        data={
            "equipment_id": "3",
            "service_date": "2026-09-03",
            "service_type": "Oil Change",
            "description": "TEST 4 - pre-harvest oil and filter",
            "cost": "168.40",
            "next_service_date": "2027-03-03",
            "notes": "",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert count(raw, "maintenance") == before + 1
    row = raw.execute(
        "SELECT * FROM maintenance WHERE description LIKE 'TEST 4%';"
    ).fetchone()
    assert row["equipment_id"] == 3
    assert row["cost"] == 168.40
    assert row["next_service_date"] == "2027-03-03"
    assert b"TEST 4 - pre-harvest oil and filter" in client.get("/equipment/3").data


def test_04b_maintenance_without_next_date_is_null_not_empty(client, raw):
    client.post(
        "/maintenance/add",
        data={"equipment_id": "1", "service_date": "2026-09-03",
              "service_type": "General Inspection",
              "description": "TEST 4b - no follow-up", "cost": "0",
              "next_service_date": "", "notes": ""},
        follow_redirects=True,
    )
    row = raw.execute(
        "SELECT * FROM maintenance WHERE description = 'TEST 4b - no follow-up';"
    ).fetchone()
    assert row is not None
    # A blank form field must become NULL, not the empty string: '' would sort
    # before every real date and show up as permanently overdue.
    assert row["next_service_date"] is None
    assert b"TEST 4b - no follow-up" in client.get("/maintenance?due=none").data


@pytest.mark.parametrize(
    "field,value,expected_fragment",
    [
        ("equipment_id", "9999", "no equipment with id 9999"),
        ("service_type", "Wash and wax", "service type"),
        ("service_date", "03/09/2026", "YYYY-MM-DD"),
        ("next_service_date", "2026-01-01", "cannot be before the service date"),
        ("cost", "-1", "cost cannot be negative"),
    ],
)
def test_04c_invalid_maintenance_rejected(client, raw, field, value, expected_fragment):
    payload = {
        "equipment_id": "1", "service_date": "2026-09-03",
        "service_type": "Oil Change", "description": "TEST 4c",
        "cost": "50", "next_service_date": "2027-03-03", "notes": "",
    }
    payload[field] = value
    before = count(raw, "maintenance")
    response = client.post("/maintenance/add", data=payload, follow_redirects=True)
    assert b"Could not save service record" in response.data
    assert expected_fragment.encode() in response.data
    assert count(raw, "maintenance") == before


# ===========================================================================
# TEST 5 — UPDATE
# ===========================================================================
def test_05_update_repair(client, raw):
    original = raw.execute("SELECT * FROM repairs WHERE repair_id = 1;").fetchone()
    assert original["cost"] != 777.77

    response = client.post(
        "/repairs/1/edit",
        data={
            "equipment_id": str(original["equipment_id"]),
            "mechanic_id": "2",                       # changed mechanic
            "repair_date": "2026-04-03",
            "problem": "TEST 5 - updated problem text",
            "repair_description": "Updated description.",
            "cost": "777.77",
            "notes": "",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    updated = raw.execute("SELECT * FROM repairs WHERE repair_id = 1;").fetchone()
    assert updated["cost"] == 777.77
    assert updated["problem"] == "TEST 5 - updated problem text"
    assert updated["mechanic_id"] == 2
    # An UPDATE, not an INSERT
    assert count(raw, "repairs") == SEED_REPAIRS


def test_05b_update_equipment_status(client, raw):
    client.post(
        "/equipment/3/edit",
        data={"name": "Case IH Axial-Flow 6150", "equipment_type": "Combine",
              "manufacturer": "Case IH", "model": "Axial-Flow 6150", "year": "2017",
              "serial_number": "YHG6150C7L045221", "purchase_date": "2018-08-02",
              "status": "Operational"},
        follow_redirects=True,
    )
    assert raw.execute(
        "SELECT status FROM equipment WHERE equipment_id = 3;"
    ).fetchone()["status"] == "Operational"
    assert count(raw, "equipment") == SEED_EQUIPMENT


# ===========================================================================
# TEST 6 — DELETE, and ON DELETE CASCADE
# ===========================================================================
def test_06_delete_repair(client, raw):
    before = count(raw, "repairs")
    response = client.post("/repairs/2/delete", follow_redirects=True)
    assert response.status_code == 200
    assert raw.execute("SELECT * FROM repairs WHERE repair_id = 2;").fetchone() is None
    assert count(raw, "repairs") == before - 1


def test_06b_delete_equipment_cascades(client, raw):
    owned_r = raw.execute(
        "SELECT COUNT(*) AS n FROM repairs WHERE equipment_id = 5;"
    ).fetchone()["n"]
    owned_m = raw.execute(
        "SELECT COUNT(*) AS n FROM maintenance WHERE equipment_id = 5;"
    ).fetchone()["n"]
    assert owned_r > 0 and owned_m > 0

    response = client.post("/equipment/5/delete", follow_redirects=True)

    assert response.status_code == 200
    assert raw.execute(
        "SELECT * FROM equipment WHERE equipment_id = 5;"
    ).fetchone() is None
    assert raw.execute(
        "SELECT COUNT(*) AS n FROM repairs WHERE equipment_id = 5;"
    ).fetchone()["n"] == 0
    assert raw.execute(
        "SELECT COUNT(*) AS n FROM maintenance WHERE equipment_id = 5;"
    ).fetchone()["n"] == 0
    assert not raw.execute("PRAGMA foreign_key_check;").fetchall()


def test_06c_delete_mechanic_sets_null_and_keeps_the_repairs(client, raw):
    """ON DELETE SET NULL, not CASCADE: the repair still happened."""
    worked_on = raw.execute(
        "SELECT COUNT(*) AS n FROM repairs WHERE mechanic_id = 1;"
    ).fetchone()["n"]
    assert worked_on > 0
    repairs_before = count(raw, "repairs")

    response = client.post("/mechanics/1/delete", follow_redirects=True)

    assert response.status_code == 200
    assert raw.execute(
        "SELECT * FROM mechanics WHERE mechanic_id = 1;"
    ).fetchone() is None
    # the repair rows survive...
    assert count(raw, "repairs") == repairs_before
    # ...with a NULL mechanic
    assert raw.execute(
        "SELECT COUNT(*) AS n FROM repairs WHERE mechanic_id = 1;"
    ).fetchone()["n"] == 0
    assert not raw.execute("PRAGMA foreign_key_check;").fetchall()
    assert b"In-house" in client.get("/repairs").data


def test_06d_delete_from_edit_page_gives_one_clean_message(client):
    """Deleting from a record's own edit page must not bounce off a dead URL."""
    response = client.post(
        "/repairs/3/delete",
        headers={"Referer": "/repairs/3/edit"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    body = response.data.decode()
    assert "Deleted repair #3 from the database." in body
    assert "no longer exists" not in body


# ===========================================================================
# TEST 7 — Foreign key enforcement
# ===========================================================================
def test_07_foreign_keys_are_enforced(raw):
    with pytest.raises(sqlite3.IntegrityError):
        raw.execute(
            "INSERT INTO repairs (equipment_id, repair_date, problem, cost) "
            "VALUES (9999, '2026-09-03', 'orphan', 10);"
        )
    raw.rollback()
    with pytest.raises(sqlite3.IntegrityError):
        raw.execute(
            "INSERT INTO maintenance (equipment_id, service_date, service_type, cost) "
            "VALUES (9999, '2026-09-03', 'Oil Change', 10);"
        )
    raw.rollback()


def test_07b_foreign_keys_off_would_allow_the_orphan(db_path):
    """Proof that PRAGMA foreign_keys = ON is what does the work.

    Same schema, same INSERT, on a connection that never issues the PRAGMA:
    SQLite accepts the orphan row. This is AI_LEARNING_EVIDENCE.md #1.
    """
    conn = sqlite3.connect(db_path)          # deliberately NO pragma
    conn.execute(
        "INSERT INTO repairs (equipment_id, repair_date, problem, cost) "
        "VALUES (9999, '2026-09-03', 'orphan row', 10);"
    )
    conn.commit()
    orphans = conn.execute("PRAGMA foreign_key_check;").fetchall()
    conn.close()
    assert orphans, "expected foreign_key_check to report the orphan row"


def test_07c_check_constraints_are_enforced(raw):
    with pytest.raises(sqlite3.IntegrityError):
        raw.execute(
            "INSERT INTO repairs (equipment_id, repair_date, problem, cost) "
            "VALUES (1, '2026-09-03', 'negative cost', -5);"
        )
    raw.rollback()
    with pytest.raises(sqlite3.IntegrityError):
        raw.execute(
            "INSERT INTO equipment (name, equipment_type, manufacturer) "
            "VALUES ('Bad type', 'Spaceship', 'Acme');"
        )
    raw.rollback()
    with pytest.raises(sqlite3.IntegrityError):
        raw.execute(
            "INSERT INTO equipment (name, manufacturer, serial_number) "
            "VALUES ('Duplicate serial', 'Acme', '1LV5075EKKY123456');"
        )
    raw.rollback()


# ===========================================================================
# TEST 8 — WHERE filtering and ORDER BY sorting through the interface
# ===========================================================================
def test_08_filter_and_sort(client, raw):
    expected = raw.execute(
        "SELECT COUNT(*) AS n FROM repairs WHERE equipment_id = 1;"
    ).fetchone()["n"]
    page = client.get("/repairs?equipment_id=1").data.decode()
    assert f"{expected} repair" in page

    # in-house filter: mechanic_id IS NULL
    inhouse = raw.execute(
        "SELECT COUNT(*) AS n FROM repairs WHERE mechanic_id IS NULL;"
    ).fetchone()["n"]
    assert f"{inhouse} repair" in client.get("/repairs?mechanic_id=none").data.decode()

    # a filter that matches nothing
    empty = client.get("/repairs?min_cost=999999").data.decode()
    assert "0 repairs" in empty
    assert "No repairs match those filters" in empty

    # equipment search across four columns
    assert b"John Deere 5075E" in client.get("/equipment?search=5075").data
    assert b"John Deere 5075E" in client.get("/equipment?search=1LV5075").data

    # sorting really sorts
    costs = [r["cost"] for r in raw.execute(
        "SELECT cost FROM repairs ORDER BY cost DESC;"
    )]
    assert costs == sorted(costs, reverse=True)

    # a hostile sort key falls back to the whitelist default instead of
    # reaching the SQL string
    assert client.get("/repairs?sort=1;DROP TABLE repairs--").status_code == 200
    assert count(raw, "repairs") == SEED_REPAIRS
    assert client.get("/equipment?sort=1;DROP TABLE equipment--").status_code == 200
    assert count(raw, "equipment") == SEED_EQUIPMENT


def test_08c_search_treats_percent_and_underscore_literally(client, raw):
    """Regression test for bug 1 in documentation/DEBUGGING.md.

    LIKE reads '%' as "any sequence" and '_' as "any single character", so
    before the fix, typing either of those into the search box returned EVERY
    machine instead of none. Serial numbers and model codes really do contain
    underscores, so this was not hypothetical.
    """
    total = count(raw, "equipment")
    assert total == SEED_EQUIPMENT

    for wildcard in ["%", "_", "%%", "_%"]:
        page = client.get(f"/equipment?search={wildcard}").data.decode()
        assert "0 machines" in page, (
            f"searching for a literal {wildcard!r} matched rows — "
            "the LIKE wildcard is not being escaped"
        )

    # a machine whose model genuinely contains an underscore is findable
    raw.execute(
        "INSERT INTO equipment (name, manufacturer, model, serial_number) "
        "VALUES ('Underscore Machine', 'Acme', 'X_200', 'US_0001');"
    )
    raw.commit()
    page = client.get("/equipment?search=X_200").data.decode()
    assert "Underscore Machine" in page
    assert "1 machine" in page          # exactly one, not all of them

    # ordinary searches still work
    assert b"John Deere 5075E" in client.get("/equipment?search=5075").data


def test_08d_implausible_dates_are_rejected(client, raw):
    """Regression test for bug 2: format-only date validation.

    '2099-01-01' and '1899-01-01' both match YYYY-MM-DD and are both certainly
    typing mistakes. A repair is something that already happened.
    """
    before = count(raw, "repairs")
    for bad_date, fragment in [("2099-01-01", "in the future"),
                               ("1899-01-01", "before 1900")]:
        response = client.post(
            "/repairs/add",
            data={"equipment_id": "1", "mechanic_id": "",
                  "repair_date": bad_date, "problem": "TEST 8d", "cost": "5"},
            follow_redirects=True,
        )
        assert fragment in response.data.decode()
        assert count(raw, "repairs") == before

    # but a FUTURE next_service_date is correct and must still be accepted
    response = client.post(
        "/maintenance/add",
        data={"equipment_id": "1", "service_date": "2026-09-03",
              "service_type": "Oil Change", "description": "TEST 8d scheduled",
              "cost": "100", "next_service_date": "2027-03-03", "notes": ""},
        follow_redirects=True,
    )
    assert raw.execute(
        "SELECT next_service_date FROM maintenance "
        "WHERE description = 'TEST 8d scheduled';"
    ).fetchone()["next_service_date"] == "2027-03-03"


def test_08e_costs_copied_off_an_invoice_are_accepted(client, raw):
    """Regression test for bug 3: '$1,240.75' used to be rejected outright."""
    for raw_cost, expected in [("1,240.75", 1240.75), ("$500", 500.00),
                               (" 88.50 ", 88.50), ("$1,000.00", 1000.00)]:
        response = client.post(
            "/repairs/add",
            data={"equipment_id": "1", "mechanic_id": "",
                  "repair_date": "2026-09-03",
                  "problem": f"TEST 8e {raw_cost}", "cost": raw_cost},
            follow_redirects=True,
        )
        assert b"Could not save repair" not in response.data, raw_cost
        # the app strips whitespace from the problem text, so match on that
        row = raw.execute(
            "SELECT cost FROM repairs WHERE problem = ?;",
            (f"TEST 8e {raw_cost}".strip(),),
        ).fetchone()
        assert row is not None, f"{raw_cost!r} was not stored at all"
        assert row["cost"] == expected, f"{raw_cost!r} stored as {row['cost']}"

    # genuine nonsense is still rejected
    response = client.post(
        "/repairs/add",
        data={"equipment_id": "1", "mechanic_id": "", "repair_date": "2026-09-03",
              "problem": "TEST 8e bad", "cost": "free of charge"},
        follow_redirects=True,
    )
    assert b"is not a number" in response.data


def test_08b_overdue_filter_excludes_null_next_dates(client, raw):
    """A NULL next_service_date means 'not scheduled', never 'overdue'."""
    overdue_ids = {
        r["maintenance_id"]
        for r in raw.execute(
            "SELECT maintenance_id FROM maintenance "
            "WHERE next_service_date IS NOT NULL AND next_service_date < '2026-09-04';"
        )
    }
    null_ids = {
        r["maintenance_id"]
        for r in raw.execute(
            "SELECT maintenance_id FROM maintenance WHERE next_service_date IS NULL;"
        )
    }
    assert overdue_ids and null_ids, "sample data should contain both cases"
    assert not (overdue_ids & null_ids)

    page = client.get("/maintenance?due=overdue").data.decode()
    assert f"{len(overdue_ids)} service record" in page


# ===========================================================================
# TEST 9 — CSV import
# ===========================================================================
HEADER = ("name,equipment_type,manufacturer,model,year,serial_number,"
          "purchase_date,status\n")

GOOD_CSV = HEADER + (
    "TEST 9 Fendt 942,Tractor,Fendt,942 Vario,2024,T9SERIAL0001,2024-03-01,Operational\n"
    "TEST 9 Horsch Pronto,Planter,Horsch,Pronto 6 DC,2021,T9SERIAL0002,2021-05-14,Operational\n"
)

BAD_CSV = HEADER + (
    "TEST 9 Valid Row,Tractor,Valtra,T215,2022,T9SERIAL0010,2022-01-05,Operational\n"
    ",Tractor,Kubota,M7-172,2021,T9SERIAL0011,2021-04-02,Operational\n"
    "No maker,Tractor,,X100,2020,T9SERIAL0012,2020-01-01,Operational\n"
    "Bad type,Harvester,Krone,BiG M,2019,T9SERIAL0013,2019-05-15,Operational\n"
    "Bad year,Tractor,Bobcat,S650,nineteen,T9SERIAL0014,2019-06-01,Operational\n"
    "Duplicate serial,Tractor,Case IH,Magnum,2020,1LV5075EKKY123456,2020-08-11,Operational\n"
    "Bad date,Other,Claas,Jaguar,2021,T9SERIAL0015,08/11/2021,Operational\n"
    "Bad status,Planter,Kinze,3600,2017,T9SERIAL0016,2017-03-22,Broken Down\n"
)

DUPES_IN_FILE_CSV = HEADER + (
    "First copy,Tractor,Deutz,6135C,2023,SAMESERIAL123,2023-01-19,Operational\n"
    "Second copy,Tractor,Deutz,6135C,2023,SAMESERIAL123,2023-01-19,Operational\n"
)


def _upload(client, text, name="test.csv"):
    return client.post(
        "/import",
        data={"csv_file": (io.BytesIO(text.encode()), name)},
        content_type="multipart/form-data",
        follow_redirects=True,
    )


def test_09_csv_import_accepts_good_rows(client, raw):
    before = count(raw, "equipment")
    response = _upload(client, GOOD_CSV)
    assert response.status_code == 200
    assert count(raw, "equipment") == before + 2
    assert raw.execute(
        "SELECT * FROM equipment WHERE serial_number = 'T9SERIAL0001';"
    ).fetchone()["year"] == 2024


def test_09b_csv_import_rejects_bad_rows(client, raw):
    before = count(raw, "equipment")
    response = _upload(client, BAD_CSV)
    assert response.status_code == 200
    # exactly one of the eight data rows is valid
    assert count(raw, "equipment") == before + 1
    body = response.data.decode()
    for fragment in ["name is required", "manufacturer is required",
                     "equipment type", "not a whole number",
                     "already registered", "YYYY-MM-DD", "status"]:
        assert fragment in body, f"missing rejection reason: {fragment}"


def test_09c_csv_duplicate_within_the_same_file(client, raw):
    """The database check cannot catch this: neither row is inserted yet."""
    before = count(raw, "equipment")
    response = _upload(client, DUPES_IN_FILE_CSV)
    assert count(raw, "equipment") == before + 1
    assert "appears twice in this file" in response.data.decode()


def test_09d_csv_missing_columns_rejected(client, raw):
    before = count(raw, "equipment")
    response = _upload(client, "wrong,header\n1,2\n")
    assert b"missing required column" in response.data
    assert count(raw, "equipment") == before


def test_09e_csv_with_excel_bom_and_crlf(client, raw):
    """What Excel actually writes: a byte-order mark and CRLF line endings."""
    before = count(raw, "equipment")
    text = "﻿" + HEADER.replace("\n", "\r\n") + (
        " TEST 9e Claas Arion , Tractor , Claas , Arion 650 , 2020 , "
        "T9ESERIAL01 , 2020-02-02 , Operational \r\n"
    )
    response = _upload(client, text, "excel.csv")
    assert count(raw, "equipment") == before + 1, response.data.decode()[:400]
    row = raw.execute(
        "SELECT * FROM equipment WHERE serial_number = 'T9ESERIAL01';"
    ).fetchone()
    assert row["name"] == "TEST 9e Claas Arion"     # whitespace stripped
    assert row["equipment_type"] == "Tractor"


# ===========================================================================
# TEST 10 — every page renders
# ===========================================================================
@pytest.mark.parametrize(
    "path",
    ["/", "/equipment", "/equipment/add", "/equipment/1", "/equipment/1/edit",
     "/repairs", "/repairs/add", "/repairs/1/edit",
     "/maintenance", "/maintenance/add", "/maintenance/1/edit",
     "/mechanics", "/reports", "/import", "/schema", "/about"],
)
def test_10_pages_render(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert b"FarmFix" in response.data


def test_10b_missing_records_and_urls(client):
    assert client.get("/equipment/99999", follow_redirects=True).status_code == 200
    assert client.get("/repairs/99999/edit", follow_redirects=True).status_code == 200
    assert client.get("/no-such-page").status_code == 404


def test_10c_dashboard_totals_match_the_database(client, raw):
    page = client.get("/").data.decode()
    assert f"{SEED_REPAIR_COST:,.2f}" in page
    assert f"{SEED_MAINTENANCE_COST:,.2f}" in page
    assert f"{SEED_REPAIR_COST + SEED_MAINTENANCE_COST:,.2f}" in page
    assert count(raw, "repairs") == SEED_REPAIRS
    assert count(raw, "maintenance") == SEED_MAINTENANCE


# ===========================================================================
# TEST 11 — schema inspection reports what schema.sql declares
# ===========================================================================
def test_11_schema_inspection(client, raw):
    tables = {
        r[0] for r in raw.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%';"
        )
    }
    assert {"equipment", "repairs", "maintenance", "mechanics"} <= tables

    fks = raw.execute("PRAGMA foreign_key_list(repairs);").fetchall()
    assert {(f["from"], f["table"], f["on_delete"]) for f in fks} == {
        ("equipment_id", "equipment", "CASCADE"),
        ("mechanic_id", "mechanics", "SET NULL"),
    }
    mfks = raw.execute("PRAGMA foreign_key_list(maintenance);").fetchall()
    assert {(f["from"], f["table"], f["on_delete"]) for f in mfks} == {
        ("equipment_id", "equipment", "CASCADE"),
    }

    for table in ["equipment", "repairs", "maintenance", "mechanics"]:
        cols = raw.execute(f"PRAGMA table_info({table});").fetchall()
        assert any(c["pk"] for c in cols), f"{table} has no primary key"

    # equipment_id must be NOT NULL on both children; mechanic_id must NOT be
    assert next(c for c in raw.execute("PRAGMA table_info(repairs);")
                if c["name"] == "equipment_id")["notnull"] == 1
    assert next(c for c in raw.execute("PRAGMA table_info(repairs);")
                if c["name"] == "mechanic_id")["notnull"] == 0

    page = client.get("/schema").data.decode()
    for table in ["equipment", "repairs", "maintenance", "mechanics"]:
        assert table in page
    assert "PRAGMA foreign_key_check returned no rows" in page
