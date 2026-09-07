# FarmFix — Farm Equipment Repair & Maintenance Tracker

**COMP 368 Database Systems — Project 1 (Southwest MN Hackathon Preparation)**
Southwest Minnesota State University · Fall 2026

**Team:** Ayush Gaire · Ashish Gaire · AJ Rayamajhi
**Demo video:** `[PASTE ZOOM LINK]`

---

## 1. Project overview

Farmers and mechanics rely on memory, notebooks and glovebox receipts to
remember when a tractor was last serviced or what was done to it. Records get
lost, repairs get repeated, and nobody can answer the question that actually
matters at the end of a season: **which machine is costing us the most to keep
running?**

FarmFix is a small Flask web application backed by a **real SQLite3 database
file**. It stores equipment, repairs and service records in one relational
database, so a machine's full history is a query rather than a search through a
drawer — and the cost totals are recomputed from the records every time a page
loads, so they can never drift out of date.

Nothing here is faked with `localStorage`, a JSON file, a hard-coded array, or a
hosted database service. Delete `database/farmfix.db` and the application has no
data at all — it refuses to start and tells you how to rebuild it.

---

## 2. Features

| Area | What it does | Database work behind it |
|---|---|---|
| **Dashboard** | Equipment / repair / service counts, total repair cost, total maintenance cost, combined spend, service that is due or overdue, recent activity | `COUNT`, `SUM`, `AVG`, `MAX`; a `JOIN` with a date filter; a `UNION ALL` across two tables |
| **Equipment** | Register, browse, search across four columns, filter by type and status, sort by any column, edit, delete | `INSERT`; `SELECT` with dynamic `WHERE` and whitelisted `ORDER BY`; correlated subqueries for the cost columns; `UPDATE`; `DELETE` (cascades) |
| **Equipment detail** | One machine's full repair history, service history, cost totals, last service and next scheduled service | Three tables joined on `equipment_id`, plus a `LEFT JOIN` to `mechanics` |
| **Repairs** | Log, browse, filter by machine / mechanic / date range / minimum cost / text, sort, edit, delete | `INSERT`, `SELECT` with `JOIN` + `LEFT JOIN`, `UPDATE`, `DELETE` |
| **Maintenance** | Log a service, schedule the next one, filter by machine / type / overdue, sort, edit, delete | Same, plus `IS NULL` / `IS NOT NULL` handling for unscheduled follow-ups |
| **Mechanics** | Add, list with spend roll-up, remove | `LEFT JOIN` + `GROUP BY`; `DELETE` with `ON DELETE SET NULL` |
| **Reports** | Eight analyses: lifetime cost per machine, repair cost per machine, service cost per machine, spending by service type, spending by mechanic, repairs by month, problem machines, recent repairs, service schedule | `GROUP BY`, `HAVING`, correlated subqueries, `strftime`, `ORDER BY ... LIMIT` |
| **Import CSV** | Upload a machinery list; valid rows are inserted, bad rows are listed with the reason | `csv.DictReader` → validation → `executemany()` |
| **Schema** | Live inspection of the database's own metadata | `sqlite_master`, `PRAGMA table_info`, `PRAGMA foreign_key_list`, `PRAGMA index_list`, `PRAGMA foreign_key_check` |
| **About Project** | One-page explanation for the demo | Live row counts read from the database |

Every page that runs a query has a **"Show SQL"** button that reveals the exact
statement — including the bound parameters — that produced what is on screen.

---

## 3. Technology stack

| Layer | Choice | Why |
|---|---|---|
| Database | **SQLite3** via Python's standard-library `sqlite3` module | Required by the assignment; one file, no server |
| Backend | **Python 3.9+ / Flask 3** | Small enough that all three of us can read the whole file |
| Frontend | **HTML** (Jinja2 templates), **CSS** (hand-written), **JavaScript** (about 20 lines, vanilla) | No build step, no framework to explain |
| Testing | pytest | Runs against a throwaway copy of the database |
| **No ORM** | raw SQL throughout | So every statement can be read aloud and defended in the demo |

---

## 4. Database structure

Four tables, derived directly from the UML class diagram in
`uml/uml-diagram.png`. Full reasoning: `documentation/UML_MAPPING.md`.

```
                      equipment
        (equipment_id PK, name, equipment_type,
         manufacturer, model, year,
         serial_number UNIQUE, purchase_date, status)
                    │ 1                │ 1
                    │                  │
                    │ 0..*             │ 0..*
              repairs                maintenance
   (repair_id PK,                (maintenance_id PK,
    equipment_id FK NOT NULL,     equipment_id FK NOT NULL,
    mechanic_id  FK NULL,         service_date, service_type,
    repair_date, problem,         description, cost,
    repair_description,           next_service_date, notes)
    cost, notes)
                    │ 0..*
                    │
                    │ 0..1
                 mechanics
      (mechanic_id PK, name, shop, phone, specialty)
```

- **`equipment` 1 → 0..\* `repairs`** — `repairs.equipment_id` is a `NOT NULL`
  foreign key, `ON DELETE CASCADE`.
- **`equipment` 1 → 0..\* `maintenance`** — same rule.
- **`mechanics` 0..1 → 0..\* `repairs`** — `repairs.mechanic_id` is
  **nullable**, `ON DELETE SET NULL`. A repair the operator does in-house has no
  mechanic on record, and removing a mechanic from the contact list must not
  delete the repairs they worked on.

Both core associations are one-to-many, so the foreign key goes on the "many"
side and **no junction table is needed** — a junction table is the right answer
to a many-to-many and the wrong answer to a one-to-many.

Foreign keys are enforced: the application issues `PRAGMA foreign_keys = ON` on
every connection, because SQLite ships with enforcement **off** and the setting
lives on the connection rather than in the file.

---

## 5. Requirements

- **Python 3.9 or newer** (developed and tested on Python 3.11)
- **pip**
- No database server, no account, no API key, no internet connection.

```bash
python3 --version
```

---

## 6. Installation

```bash
# 1. Unzip the project and enter the folder
cd farmfix

# 2. (Recommended) create a virtual environment
python3 -m venv venv
source venv/bin/activate          # macOS / Linux
venv\Scripts\activate             # Windows

# 3. Install the one dependency
pip install -r requirements.txt
```

---

## 7. How to initialize the database

The project already ships with a populated `database/farmfix.db`, so you can go
straight to step 8. To rebuild it from scratch at any time:

```bash
python database/init_db.py
```

It drops and recreates all four tables from `database/schema.sql`, loads
`database/sample_data.sql`, then reads the result back out of SQLite's own
metadata:

```
FarmFix database initialisation
  target : .../database/farmfix.db
  status : rebuilding existing file
  [ok] applied schema (schema.sql)
  [ok] applied sample data (sample_data.sql)

  Tables created (read back from sqlite_master):
    - equipment    9 columns, 0 foreign key(s), 5 row(s)
    - maintenance  8 columns, 1 foreign key(s), 11 row(s)
    - mechanics    5 columns, 0 foreign key(s), 3 row(s)
    - repairs      8 columns, 2 foreign key(s), 10 row(s)

  Foreign key integrity check: clean

  Seeded totals: repairs $4,381.20 | maintenance $2,014.75
```

Running it again is safe — it always rebuilds from scratch. **Run it right
before recording the demo** so the numbers in `documentation/DEMO_SCRIPT.md`
match exactly.

---

## 8. How to run the application

```bash
python app.py
```

Then open <http://127.0.0.1:5000>. Press `Ctrl+C` to stop.

---

## 9. How to test the application

```bash
python -m pytest tests/ -v
```

**65 test cases, all passing, in about 1.5 seconds.** Each one builds a fresh
throwaway database in a temporary folder from `schema.sql` + `sample_data.sql`,
so the tests never modify `database/farmfix.db`.

Expected final line:

```
65 passed in 1.43s
```

Full expected-vs-actual results for every case: `documentation/TESTING.md`.

### Trying the CSV import

| File | Contents |
|---|---|
| `data/sample_equipment.csv` | 5 clean rows — all should import |
| `data/sample_equipment_with_errors.csv` | 2 good rows and 7 deliberately broken ones, one per validation rule |

Go to **Import CSV**, upload either file, and the result panel lists exactly
which rows were inserted and why the others were rejected.

---

## 10. Sample login information

**None — the application has no login.** User accounts and passwords were out of
scope for a database-design project, and leaving them out keeps the demo short.
This is listed under known limitations below.

---

## 11. Project folder structure

```
farmfix/
├── app.py                        Flask application — all routes and SQL
├── requirements.txt              Flask (+ pytest for the test suite)
├── README.md                     this file
│
├── database/
│   ├── farmfix.db                the actual SQLite3 database file
│   ├── schema.sql                CREATE TABLE statements, PKs, FKs, CHECKs, indexes
│   ├── sample_data.sql           INSERT statements for the seed data
│   └── init_db.py                builds farmfix.db from the two .sql files
│
├── templates/                    Jinja2 HTML templates
│   ├── base.html                 shared layout and navigation
│   ├── dashboard.html            equipment.html        equipment_detail.html
│   ├── equipment_form.html       repairs.html          repair_form.html
│   ├── maintenance.html          maintenance_form.html mechanics.html
│   ├── reports.html              import.html           schema.html
│   └── about.html                error.html
│
├── static/
│   └── style.css                 all styling (no framework, no build step)
│
├── data/
│   ├── sample_equipment.csv               5 valid rows
│   └── sample_equipment_with_errors.csv   rows exercising every validation rule
│
├── uml/
│   ├── uml-diagram.png           rendered UML CLASS diagram
│   ├── uml-diagram.pdf           the same diagram, print-ready
│   ├── uml-diagram.svg           vector version
│   ├── uml-diagram.html          opens in a browser, prints cleanly to PDF
│   ├── uml-diagram.mmd           bare Mermaid source (for mmdc)
│   └── uml-source.md             Mermaid + PlantUML source, with explanation
│
├── documentation/
│   ├── FINAL_REPORT.md           the written report (sections 1–11)
│   ├── AI_LEARNING_EVIDENCE.md   documented AI interactions, including wrong ones
│   ├── UML_MAPPING.md            UML class → relational table mapping
│   ├── TESTING.md                test table with expected vs actual results
│   ├── DEBUGGING.md              real bugs: symptom → cause → fix → retest
│   ├── DEMO_SCRIPT.md            3–5 minute Zoom demo plan with speaking parts
│   ├── D2L_DISCUSSION.md         ready-to-paste discussion post
│   └── FINAL_CHECKLIST.md        assignment requirement checklist
│
└── tests/
    └── test_app.py               65 automated test cases
```

---

## 12. Known limitations

Listed honestly, because a database course is a bad place to overstate what
software does:

1. **No authentication.** Anyone with the URL can add or delete anything. Real
   multi-user use would need a `users` table, hashed passwords and sessions.
2. **Single-user server.** Flask's development server is not a production
   server, and SQLite allows only one writer at a time. Fine for one farm on one
   laptop; wrong for a dealership with twenty terminals.
3. **Money is stored as `REAL`.** Fine at this scale, but floating-point
   arithmetic can drift by fractions of a cent over thousands of rows. A
   production system would store integer cents.
4. **`year` is only range-checked, not sanity-checked against today.** A model
   year of 2030 is accepted in 2026. Manufacturers do sell next-year models, so
   we chose not to over-constrain it; 1750 is still rejected.
5. **No photo or document attachments.** A real maintenance log would hold
   invoice scans and photos of the failed part. Storing files was out of scope.
6. **CSV import is partial-commit.** Valid rows are inserted even when other
   rows in the same file fail. This matches what people expect from a
   spreadsheet import, but it means a half-imported file has to be cleaned up by
   hand.
7. **CSV import covers equipment only.** Repairs and services must be entered
   through the forms, because they need a resolved foreign key.
8. **No recurring-service rule.** `next_service_date` is typed in by hand each
   time rather than being generated from an interval (for example "every 250
   hours"). Hour meters are not modelled at all.
9. **Deleting a machine deletes its history.** That is what `ON DELETE CASCADE`
   means, and it is the right rule for a mistyped entry — but a farm selling a
   machine would probably rather archive it. Setting its status to `Retired` is
   the workaround.

---

## 13. Quick reference

```bash
pip install -r requirements.txt   # install
python database/init_db.py        # (re)build the database
python app.py                     # run  → http://127.0.0.1:5000
python -m pytest tests/ -v        # test
```
