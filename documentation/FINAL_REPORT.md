# FarmFix — Farm Equipment Repair & Maintenance Tracker

## Final Written Report

**COMP 368 Database Systems — Project 1 (Southwest MN Hackathon Preparation)**
Southwest Minnesota State University · Fall 2026

---

## 1. Team / Project Title

**FarmFix — Farm Equipment Repair & Maintenance Tracker**

**Course:** COMP 368 Database Systems
**Assignment:** Project 1 — AI-Assisted SQLite3 Learning · UML Conceptual Design ·
Open Database Application Development

**One-line description:** A Flask web application backed by a real SQLite3
database that gives a farm one organised place to register equipment, record
repairs and services, see a machine's full history, and find out which machine
is costing the most to keep running.

---

## 2. Team Members

- **Ayush Gaire**
- **Ashish Gaire**
- **AJ Rayamajhi**

---

## 3. Problem and Application Idea

### 3.1 The problem

Farm equipment is expensive, it is used hard for a few intense weeks a year, and
it fails at the worst possible moment. What keeps it running is knowing its
history — but that history is kept in the worst possible places: in someone's
memory, in a notebook in the shop, in receipts in the glovebox, on a text message
to a mechanic.

The consequences are concrete:

- **Lost maintenance history.** Nobody can say when the combine's hydraulic
  system was last serviced.
- **Forgotten repairs.** A known problem recurs and nobody remembers what fixed
  it last time.
- **Repeated repairs.** The same part is replaced twice because two people are
  looking after the same machine.
- **No cost visibility.** Money leaves in $40 and $600 pieces across five
  machines and a year, and nobody can say which machine is the expensive one.
- **Missed service intervals.** An oil change is due, but the only reminder was
  a note on a whiteboard that got wiped.

The last two are the ones that cost real money, and they are the ones that are
impossible to answer without relating records to each other. *"Which machine
cost us the most this year?"* means totalling two different kinds of record,
grouped by machine, and comparing. That is not a question a notebook can answer.

### 3.2 Why this is a database problem, not a spreadsheet problem

A spreadsheet can hold a list of repairs. What it cannot do well is keep the
*relationship* between a machine and its history correct: one sheet per machine
duplicates the machine's details on every row, so renaming a tractor means
editing dozens of cells and getting one wrong. And every summary has to be
recomputed by hand, so it is stale the moment a new repair is entered.

In FarmFix, a machine's details are stored once and referenced by
`equipment_id`; the cost totals are **queries**, recomputed from the underlying
records every time a page loads, so they can never drift out of date.

### 3.3 Target users

- **Farmers and farm owners** tracking their own machinery.
- **Farm mechanics** who need to see what has already been tried on a machine
  before starting work.
- **Equipment operators** logging a fault at the end of a shift.

### 3.4 The application

FarmFix stores four things — **equipment**, **repairs**, **maintenance** and
**mechanics** — and provides:

- a dashboard of fleet counts, total repair and maintenance spend, service that
  is due or overdue, and a combined activity feed;
- an equipment register with search, filtering, sorting and full CRUD;
- an **equipment detail page** showing one machine's complete repair and service
  history with cost roll-ups — the page where the relational design pays off;
- repair and maintenance registers, each with filtering, sorting and full CRUD;
- eight cost and scheduling reports;
- a CSV importer for loading an existing machinery list;
- a live schema-inspection page.

### 3.5 Why this idea satisfies the assignment

| Requirement | How the idea provides it naturally |
|---|---|
| At least two meaningful related tables | Four, all of which the problem genuinely needs |
| Primary keys | One per entity |
| Foreign keys | Three, with **three different** `ON DELETE` behaviours, so the choice is a real design decision rather than a formality |
| `INSERT` / `SELECT` / `UPDATE` / `DELETE` | Registering a machine, browsing its history, correcting a cost and removing a mistyped record are the four things a user actually does |
| `WHERE` | "Show me only the hydraulic jobs on the combine" is the normal way to use the register |
| `ORDER BY` | "What was the most expensive repair?" |
| `GROUP BY` + aggregates | The entire cost-reporting layer |
| `JOIN` | Repairs store an `equipment_id`, not a machine name — every readable screen needs a join |
| CSV import | Farms already keep a machinery list in a spreadsheet; importing one is a real need, not a bolted-on demo |

We deliberately chose a scope small enough that all three of us can explain every
table and every query, rather than one that would look more impressive and be
harder to defend.

### 3.6 What we deliberately left out

This is a simplified academic version of a larger FarmFix concept. Removed on
purpose: payments and subscription tiers, hosted databases, third-party
authentication, maps, external API dependencies, permission systems, and any
chatbot. None of them would have demonstrated a database concept the four tables
do not already demonstrate, and each one would have made the project harder to
explain.

---

## 4. AI-Assisted SQLite3 Learning

Full transcripts and verification steps: **`documentation/AI_LEARNING_EVIDENCE.md`**.
This section summarises them.

### 4.1 SQLite3 concepts learned

| # | Concept | Where it shows up |
|---|---|---|
| 1 | **What SQLite3 is** — an *embedded* engine; the database is one file and the engine runs inside the application process | `database/farmfix.db`; About Project page |
| 2 | **How it differs from a server DBMS** — no server, host, port or credentials; one writer at a time; dynamic typing; foreign keys off by default | §4.2 below |
| 3 | **Creating / opening a database** — `sqlite3.connect(path)` creates the file if it does not exist | `database/init_db.py` |
| 4 | **`CREATE TABLE`** | `database/schema.sql` |
| 5 | **Data types** — five storage classes, and *type affinity* rather than strict typing | All four `CREATE TABLE` statements; Schema page shows declared types live |
| 6 | **Primary keys** — `INTEGER PRIMARY KEY` aliases the internal `rowid` and auto-increments without `AUTOINCREMENT` | All four tables |
| 7 | **Foreign keys** — declared in `CREATE TABLE` but **not enforced** without `PRAGMA foreign_keys = ON`, per connection | `schema.sql`; `get_db()`; tests 7 / 7b |
| 8 | **`INSERT`** | Four add forms; CSV import; `sample_data.sql` |
| 9 | **`SELECT`** | Every page |
| 10 | **`UPDATE`** | Edit forms for equipment, repairs and maintenance |
| 11 | **`DELETE`** | Delete on all four tables |
| 12 | **`WHERE`** | Every filter; `LIKE` with `ESCAPE`; `IS NULL` / `IS NOT NULL` |
| 13 | **`ORDER BY`** | Sortable column headings on three pages |
| 14 | **`GROUP BY`** and **`HAVING`** | Reports page; Mechanics page |
| 15 | **Aggregates** `COUNT` `SUM` `AVG` `MIN` `MAX` | Dashboard tiles; every report |
| 16 | **`JOIN`** — INNER vs LEFT, and what a join does to the *number of rows* | Equipment detail; every report; §4.5 |
| 17 | **Schema inspection** — `sqlite_master`, `PRAGMA table_info`, `PRAGMA foreign_key_list`, `PRAGMA index_list`, `PRAGMA foreign_key_check` | The whole Schema page; `init_db.py` output |
| 18 | **Testing SQL queries** — running a statement standalone and reconciling the numbers before wiring it into a page | 65 pytest cases; `documentation/TESTING.md` |
| 19 | **Importing from CSV / Excel** | `/import`; the pandas approach documented on that page |
| 20 | **Connecting SQLite3 to the backend** | `app.get_db()` with `sqlite3.Row` and per-request teardown |

Beyond the required list we also used `UNION ALL` (dashboard activity feed),
correlated subqueries (cost roll-ups), `COALESCE`, `strftime`, `LIKE … ESCAPE`,
and explicit indexes on the foreign-key columns.

### 4.2 SQLite3 versus a server-based DBMS

| | SQLite3 | MySQL / PostgreSQL |
|---|---|---|
| Architecture | Library linked into the application; no separate process | Client/server; a daemon runs continuously |
| The database is | One file (`farmfix.db`) you can copy onto a USB stick | A managed data directory on a server |
| Connecting | `sqlite3.connect("database/farmfix.db")` | Host, port, database, username, password |
| Users / permissions | None — filesystem permissions are the security model | `CREATE USER`, `GRANT`, roles |
| Concurrency | Many readers, **one writer at a time** | Many concurrent writers, row-level locking |
| Typing | Dynamic; declared types are *affinities* | Strict — `'nineteen'` into an `INTEGER` column is an error |
| Foreign keys | Declared but **off by default** | Enforced automatically |
| Good for | Embedded apps, single-user tools, prototypes, this project | Multi-user production systems |

The last two rows changed our code. Because SQLite typing is loose and foreign
keys are off by default, **application-side validation is load-bearing here in a
way it would not be on PostgreSQL** — which is why `validate_equipment()`,
`validate_repair()` and `validate_maintenance()` exist, and why the CSV importer
reuses exactly the same functions as the web forms.

It is also why a farm is a good fit for SQLite in the first place: one laptop in
the farm office, no server to administer, and the whole database is a file you
can back up by copying it.

### 4.3 The three most important AI interactions

**Interaction 1 — "My foreign key isn't doing anything."**
We inserted a repair with `equipment_id = 9999` and SQLite accepted it despite a
`FOREIGN KEY` clause. The AI identified the cause: SQLite disables foreign-key
enforcement by default for backwards compatibility, and `PRAGMA foreign_keys = ON`
must be issued **on every connection** — it is not stored in the file. We added
it in all three places that open the database, and `init_db.py` now prints
`PRAGMA foreign_key_check` output when it builds. *Verified* by writing two
tests: one asserting the orphan is rejected **with** the PRAGMA, one asserting
the same statement is **accepted** without it. Identical schema, identical
INSERT, different result — which proves the PRAGMA is what does the work.

**Interaction 2 — the cost report that tripled every total.** *(See §4.5.)*

**Interaction 3 — the search box that matched everything.** *(See §4.5.)*

Three further interactions — choosing between `CASCADE` / `SET NULL` /
`RESTRICT`, storing dates when SQLite has no DATE type, and safely sorting by a
user-chosen column — are documented in full in `AI_LEARNING_EVIDENCE.md`.

### 4.4 How SQL and code were verified

We treated AI output as a draft to be checked, never as an answer:

1. **Run the SQL standalone first**, against the real database, before wiring it
   into a page.
2. **Make the numbers reconcile.** The five per-machine repair totals sum to
   $4,381.20, which equals `SELECT SUM(cost) FROM repairs`. The seven monthly
   totals sum to the same figure. If a `JOIN` had duplicated rows, neither would
   balance — and in one case neither did (§4.5).
3. **Compute it twice, two different ways.** `test_03` derives the per-machine
   totals with SQL `GROUP BY` and again with a Python loop, and asserts they
   match.
4. **Write the test that fails against the wrong version.** A test that passes
   both before and after a fix has verified nothing.
5. **Check the database, not just the page.** Every CRUD test asserts on row
   counts and column values read through a **separate raw connection**, so a
   page that looks right but wrote nothing cannot pass.
6. **Deliberately try to break it.** Empty database, `%` in the search box, a
   year with a slipped digit, a cost pasted off an invoice, a hostile sort key,
   an Excel CSV with a byte-order mark. Three of our four bugs came from this
   step and from nowhere else.

### 4.5 AI suggestions that were wrong and had to be corrected

**(a) The lifetime-cost report — valid SQL, wrong numbers.**

We asked for one query giving, per machine, the repair count and total, the
service count and total, and the two added together. The AI produced the obvious
thing:

```sql
SELECT e.name,
       COUNT(DISTINCT r.repair_id)      AS repair_n,
       COALESCE(SUM(r.cost), 0)         AS repair_total,
       COUNT(DISTINCT m.maintenance_id) AS service_n,
       COALESCE(SUM(m.cost), 0)         AS service_total
FROM equipment e
LEFT JOIN repairs r     ON r.equipment_id = e.equipment_id
LEFT JOIN maintenance m ON m.equipment_id = e.equipment_id
GROUP BY e.equipment_id, e.name;
```

It runs, returns no error, and is wrong. Joining **two independent child
tables** to the same parent produces the cross product of the children: a machine
with 3 repairs and 3 services yields 9 rows, so every cost is counted three
times.

| Machine | True repair total | AI query's total | Rows the join produced |
|---|---|---|---|
| John Deere 5075E | **$994.30** | $2,982.90 | 9 (3 × 3) |
| Kubota L3902 | **$483.00** | $966.00 | 4 |
| Case IH Axial-Flow 6150 | **$2,021.00** | $4,042.00 | 4 |
| John Deere 1775NT | **$512.60** | $1,025.20 | 2 |
| New Holland BR7060 | **$370.30** | $740.60 | 4 |

The `COUNT(DISTINCT ...)` the AI added — which reads as careful, defensive SQL —
keeps the *counts* correct next to sums that are 200–300 % too high, which is
exactly what stops you noticing.

**How we found it:** by reconciling the report against
`SELECT SUM(cost) FROM repairs`. It did not balance.

**The fix:** a correlated subquery per total, so each table is aggregated
independently and nothing multiplies. We rejected `SUM(DISTINCT cost)`, which is
*worse* — two repairs that each cost exactly $55.00 would collapse into one,
swapping a visible over-count for an invisible under-count.

**Verified by** `test_03b_lifetime_cost_is_not_inflated_by_a_double_join`, which
asserts the application's query matches the truth for all five machines *and*
asserts the naive version really does produce $2,982.90 where the truth is
$994.30 — so that nobody re-simplifies the query later.

**(b) The search box — "parameterised, therefore safe" is a half-truth.**

The AI wrote our equipment search as `LIKE ?` with the term bound as a
parameter, and correctly noted this is not vulnerable to SQL injection. That was
true and too narrow. A bound parameter protects the SQL **statement**; it does
not stop the value being read as a **LIKE pattern**. Typing `%` built the
pattern `'%%%'` and returned **all five machines**; typing `_` did the same.
Machinery model codes genuinely contain underscores, so a user searching for
model `X_200` would get back the entire fleet.

**How we found it:** by deliberately typing awkward characters into the search
box. Using it normally never revealed it, and it raised no error.

**The fix:** escape `%`, `_` and the escape character itself in the term, and add
`ESCAPE '\'` to every `LIKE` clause. Verified before and after:
`%` went from 5 matches to 0, while `5075` still returns 1 and `Deere` still
returns 2. Regression test:
`test_08c_search_treats_percent_and_underscore_literally`.

Two further defects — dates validated for *format* but not for *plausibility*
(`2099-01-01` was accepted), and costs pasted off an invoice (`$1,240.75`) being
rejected — are written up in `documentation/DEBUGGING.md` as bugs 3 and 4.

---

## 5. UML Conceptual Database Design

The diagram is a **UML class diagram**, not an ER diagram. Rendered image:
`uml/uml-diagram.png` (also `.pdf`, `.svg`, and `.html` for printing). Source:
`uml/uml-diagram.mmd` (Mermaid) and a PlantUML version in `uml/uml-source.md`.

```
┌───────────────────────────────┐              ┌──────────────────────────┐
│           Equipment           │              │        Mechanic          │
├───────────────────────────────┤              ├──────────────────────────┤
│ «PK» equipment_id   : int     │              │ «PK» mechanic_id : int   │
│      name           : String  │              │      name      : String  │
│      equipment_type : String  │              │      shop      : String  │
│      manufacturer   : String  │              │      phone     : String  │
│      model          : String  │              │      specialty : String  │
│      year           : int     │              ├──────────────────────────┤
│      serial_number «unique»   │              │ repairCount() : int      │
│      purchase_date  : Date    │              └──────────────────────────┘
│      status         : String  │                        │ 0..1
├───────────────────────────────┤                        │
│ totalRepairCost()      : Real │                        │ performs
│ totalMaintenanceCost() : Real │                        │
│ lastServiceDate()      : Date │                        │ 0..*
└───────────────────────────────┘              ┌──────────────────────────┐
      │ 1                 │ 1        has       │         Repair           │
      │                   └────────────────────┤──────────────────────────┤
      │                              0..*      │ «PK» repair_id : int     │
      │                                        │  repair_date   : Date    │
      │ receives                               │  problem       : String  │
      │                                        │  repair_description      │
      │ 0..*                                   │  cost          : Real    │
┌──────────────────────────┐                   │  notes         : String  │
│      Maintenance         │                   ├──────────────────────────┤
├──────────────────────────┤                   │ isInHouse() : Boolean    │
│ «PK» maintenance_id      │                   └──────────────────────────┘
│  service_date   : Date   │
│  service_type   : String │
│  description    : String │
│  cost           : Real   │
│  next_service_date : Date│
│  notes          : String │
├──────────────────────────┤
│ isOverdue() : Boolean    │
└──────────────────────────┘
```

*(ASCII approximation for readers of this file — the authoritative diagram is
`uml/uml-diagram.png`.)*

### 5.1 Classes and identifiers

| Class | Identifier | Attributes |
|---|---|---|
| `Equipment` | `equipment_id` | `name`, `equipment_type`, `manufacturer`, `model`, `year`, `serial_number` *(unique)*, `purchase_date`, `status` |
| `Repair` | `repair_id` | `repair_date`, `problem`, `repair_description`, `cost`, `notes` |
| `Maintenance` | `maintenance_id` | `service_date`, `service_type`, `description`, `cost`, `next_service_date`, `notes` |
| `Mechanic` | `mechanic_id` | `name`, `shop`, `phone`, `specialty` |

`serial_number` is the **natural key** — it is stamped on the frame.
`equipment_id` is a **surrogate key**, so that correcting a mistyped serial never
means rewriting foreign keys.

The operations shown on the classes (`totalRepairCost()`, `isOverdue()`,
`isInHouse()`) are **derived** values, computed by query. They are deliberately
not stored, because a stored total goes stale the moment a repair is added.

### 5.2 Associations and multiplicities

| Association | Left | Right | Reading |
|---|---|---|---|
| Equipment **has** Repair | `1` | `0..*` | Every repair was performed on exactly one machine. A machine may have no repairs yet, or many. |
| Equipment **receives** Maintenance | `1` | `0..*` | Every service record belongs to exactly one machine. |
| Mechanic **performs** Repair | `0..1` | `0..*` | A repair was performed by at most one mechanic — **or by nobody on record**, when the operator did it themselves. |

### 5.3 Why the multiplicities are what they are

**Why `1` and not `0..1` on the Equipment side?** A repair or service belonging
to no machine could never appear in a history or a cost roll-up — it would be
invisible money. The schema enforces this with `NOT NULL`.

**Why `0..1` and not `1` on the Mechanic side?** This is the one place the domain
pushed back on a tidier model. Three of our ten sample repairs — a retensioned
belt, a plugged tire, a spring from the parts bin — were done in the shop with no
invoice and no mechanic. Forcing a mechanic onto every repair would mean
inventing a fake "Self" row that pollutes the mechanic list and distorts every
per-mechanic report. `NULL` says exactly what is true: *no mechanic on record.*

That single decision has a direct consequence in the SQL: **every screen showing
a repair alongside its mechanic must use a `LEFT JOIN`.** An inner join would
silently drop all three in-house repairs from the history and from the totals.

### 5.4 Why there is no many-to-many

Both core associations are genuinely one-to-many — one repair happens to one
machine, on one day. A junction table would let a single repair belong to two
tractors, which is not true of the real world and would double-count it in every
cost report. **A junction table is the right answer to a many-to-many and the
wrong answer to a one-to-many.**

`Mechanic → Repair` is not a candidate either: a repair has at most one mechanic,
so a nullable foreign key is the correct translation.

If FarmFix were extended to track **parts**, a junction table would appear
immediately and naturally — one repair uses many parts, one part number is used
in many repairs — and `repair_parts(repair_id, part_id, quantity, unit_price)`
would be the association table. We left it out to keep the project at a size all
three of us can explain.

---

## 6. UML-to-Relational Mapping

Full rationale, column by column: **`documentation/UML_MAPPING.md`**.
Executable version: **`database/schema.sql`**.

### 6.1 The rules applied

| UML construct | Relational construct |
|---|---|
| Class | Table |
| Attribute | Column with a SQLite type affinity |
| Identifier «PK» | `PRIMARY KEY` |
| One-to-many association | Foreign key on the **many** side |
| Multiplicity `1` on the parent | `NOT NULL` on the child's foreign key |
| Multiplicity `0..1` on the parent | **Nullable** foreign key |
| Business uniqueness rule | `UNIQUE` constraint |
| Restricted value list | `CHECK (... IN (...))` — SQLite has no `ENUM` |

### 6.2 The four tables

| UML class | Table | Primary key | Foreign keys | Rows shipped |
|---|---|---|---|---|
| `Equipment` | `equipment` | `equipment_id INTEGER PRIMARY KEY` | — | 5 |
| `Mechanic` | `mechanics` | `mechanic_id INTEGER PRIMARY KEY` | — | 3 |
| `Repair` | `repairs` | `repair_id INTEGER PRIMARY KEY` | `equipment_id` → `equipment` (NOT NULL, CASCADE); `mechanic_id` → `mechanics` (nullable, SET NULL) | 10 |
| `Maintenance` | `maintenance` | `maintenance_id INTEGER PRIMARY KEY` | `equipment_id` → `equipment` (NOT NULL, CASCADE) | 11 |

```sql
CREATE TABLE repairs (
    repair_id          INTEGER PRIMARY KEY,
    equipment_id       INTEGER NOT NULL,
    mechanic_id        INTEGER,                       -- NULL = done in-house
    repair_date        TEXT    NOT NULL,
    problem            TEXT    NOT NULL,
    repair_description TEXT,
    cost               REAL    NOT NULL DEFAULT 0 CHECK (cost >= 0),
    notes              TEXT,
    FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id) ON DELETE CASCADE,
    FOREIGN KEY (mechanic_id)  REFERENCES mechanics(mechanic_id)  ON DELETE SET NULL
);
```

### 6.3 Data types

- **`INTEGER PRIMARY KEY`**, not `... AUTOINCREMENT`. In SQLite the former is an
  alias for the internal `rowid` and auto-increments on its own; `AUTOINCREMENT`
  only adds a bookkeeping table and is needed only when ids must never be reused.
- **Dates as `TEXT`.** SQLite has **no DATE type**. Dates are stored as ISO
  `'YYYY-MM-DD'`, which sorts chronologically as plain text and works with
  `strftime()`. This is the officially recommended approach.
- **`cost REAL`** with `CHECK (cost >= 0)` — not `> 0`, because a warranty repair
  genuinely costs nothing and recording it as $0.00 is more useful than not
  recording it.
- **`CHECK (... IN (...))`** for `equipment_type`, `status` and `service_type`,
  because SQLite has no `ENUM`. This is what makes the database — not just the
  Python — reject `'Spaceship'`.

### 6.4 Why each relationship was implemented that way

**Two one-to-many associations → a foreign key on each child.** The rule is to
put the foreign key on the *many* side. Both `repairs` and `maintenance` carry
`equipment_id`. A junction table here would be wrong: it would permit one repair
to belong to two machines, which multiplicity `1` forbids and which would
double-count that repair in every cost report.

**Three foreign keys, three different `ON DELETE` behaviours.** Each answers the
same question — *what does this record mean if its parent disappears?*

| Foreign key | Action | Reasoning |
|---|---|---|
| `repairs.equipment_id` | `CASCADE` | A repair is *owned* by a machine. Scrap the machine and the history has no subject. A composition. |
| `maintenance.equipment_id` | `CASCADE` | Same reasoning. |
| `repairs.mechanic_id` | `SET NULL` | A mechanic merely *performed* the work. Removing them from the contact list must not erase the fact that the repair happened and cost $615.40 — that money still left the farm. |

*Verified:* `test_06b` (cascade removes the history), `test_06c` (set-null keeps
the repairs and only clears the mechanic), `test_11` (the declared actions are
exactly those three, so a later schema edit cannot silently change them).

**Nullable `next_service_date`, and why the `NULL` matters.** A one-off
inspection does not always book a follow-up, so "not scheduled" is a real state —
and it is not the same as "overdue". Every query touching this column says
`IS NOT NULL` explicitly, and the validator converts a blank form field to `None`
rather than `''`, because `'' <= '2026-10-19'` is **true** and a blank string
would show up as permanently overdue.

**Foreign key enforcement.** `PRAGMA foreign_keys = ON` is issued in `get_db()`,
`init_db.py`, and the test fixtures. Without it, the `FOREIGN KEY` clauses would
be documentation only. *Verified:* tests 7 and 7b.

### 6.5 Indexes and normalisation

SQLite indexes primary keys and `UNIQUE` columns automatically but **not** the
child side of a foreign key — and every join and filter in this application uses
exactly those columns, so `schema.sql` creates five explicit indexes.

The schema is in **third normal form**. `repairs` stores `mechanic_id`, never
`mechanic_name` — which is the whole reason the `mechanics` table exists.
Without it, the same person gets typed as "Dale Hutchins", "Dale H." and "dale
hutchins", and the *"spending by mechanic"* report splits one mechanic into three
rows that each look small.

---

## 7. Application Development

### 7.1 Technologies

| Layer | Choice | Reason |
|---|---|---|
| Database | **SQLite3** via Python's standard-library `sqlite3` | Required; no server, nothing to install |
| Backend | **Python 3 + Flask 3** | Small enough that all three of us can read the whole file |
| Frontend | **HTML** (Jinja2), **CSS** (hand-written), **JavaScript** (~20 lines, vanilla) | No build step, no framework to explain |
| Testing | pytest | Runs against a throwaway database copy |
| **No ORM** | raw SQL throughout | So every statement can be read aloud and defended |

One runtime dependency (`Flask`). `requirements.txt` deliberately does not list
SQLite3, because there is nothing to install.

### 7.2 SQLite3 integration

```python
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row       # read columns by name
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db

@app.teardown_appcontext
def close_db(_exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()
```

One connection per request, stored on Flask's request-scoped `g`, closed
automatically when the request ends. `sqlite3.Row` lets templates write
`row["name"]` instead of `row[1]`.

**Every value that comes from a user is a bound `?` parameter.** Column names
cannot be parameterised, so the user's sort choice is mapped through a whitelist
dictionary and an unrecognised key falls back to the default. *Verified:* test 8
sends `?sort=1;DROP TABLE repairs--` to two pages; both tables survive.

### 7.3 Frontend

Sixteen pages behind one navigation bar: Dashboard, Equipment (list / detail /
add / edit), Repairs (list / add / edit), Maintenance (list / add / edit),
Mechanics, Reports, Import CSV, Schema, About Project.

Responsive by design — a single CSS grid pattern reflows to one column, wide
tables scroll inside their own container so the page body never scrolls
sideways, and the nav collapses to a Menu button below 900 px. *Verified:*
manual test M-13 — 11 pages at three widths, **zero** horizontal-overflow cases
and **zero** JavaScript console errors.

The palette is field green and harvest amber on a warm off-white, with
green/amber/red reserved for status — because those colours have to carry
meaning. No gradients, no animation, no glassmorphism.

**Every page that runs a query has a "Show SQL" button** revealing the exact
statement, including bound parameters. It was built for the demo, but it is how
we caught several query problems while developing.

### 7.4 Major features and CRUD

| Feature | CRUD | SQL |
|---|---|---|
| Register equipment | **C** | `INSERT INTO equipment (...) VALUES (:name, :equipment_type, ...)` |
| Log a repair | **C** | `INSERT INTO repairs (equipment_id, mechanic_id, ...)` |
| Log a service | **C** | `INSERT INTO maintenance (equipment_id, service_date, ...)` |
| Add a mechanic | **C** | `INSERT INTO mechanics (...)` |
| Import CSV | **C** | validation then one `executemany()` |
| Equipment register | **R** | `SELECT` + dynamic `WHERE` + whitelisted `ORDER BY` + correlated subqueries |
| Equipment detail | **R** | three tables joined on `equipment_id`, plus `LEFT JOIN mechanics` |
| Repairs / Maintenance lists | **R** | `JOIN` + `LEFT JOIN` + dynamic `WHERE` + `ORDER BY` |
| Dashboard / Reports / Mechanics | **R** | `GROUP BY`, `HAVING`, aggregates, `UNION ALL` |
| Schema page | **R** | `sqlite_master` + four `PRAGMA`s |
| Edit equipment / repair / service | **U** | `UPDATE ... SET ... WHERE <pk> = ?` |
| Delete equipment / repair / service / mechanic | **D** | `DELETE FROM ... WHERE <pk> = ?` |

No button in the application changes only the screen. Every one runs SQL, and
the page is re-read from the database afterwards.

### 7.5 The queries that do the work

**Equipment history — the join the assignment asks for:**

```sql
SELECT equipment.name, repairs.repair_date, repairs.problem, repairs.cost
FROM equipment
JOIN repairs ON equipment.equipment_id = repairs.equipment_id
ORDER BY repairs.repair_date DESC;
```

**Repair cost per machine — `LEFT JOIN` + `GROUP BY` + five aggregates.**
`LEFT JOIN` deliberately: an inner join drops a machine with no repairs, and on a
*cost* report "missing" reads as "we don't track it" rather than "it hasn't cost
us anything."

**Lifetime cost per machine — correlated subqueries, not two joins** (§4.5).

**`HAVING` — problem machines:**

```sql
GROUP BY e.equipment_id, e.name
HAVING COUNT(*) >= 2 AND SUM(r.cost) > 500
```

`WHERE` filters rows *before* grouping; `HAVING` filters the groups *after*. On
the shipped data this returns the Case IH combine (2 repairs, $2,021.00) and the
John Deere 5075E (3 repairs, $994.30).

**`UNION ALL` — the dashboard activity feed** stacks repairs and services from
two different tables so they can be sorted together as one list.

**`LIKE … ESCAPE '\'`** on both search boxes, so a literal `%` or `_` is searched
for literally (§4.5b).

### 7.6 CSV import

`csv.DictReader` reads the upload; every row goes through **the same
`validate_equipment()` function the web form uses**, so an imported row is held
to identical rules; surviving rows are inserted with one `executemany()`;
rejected rows are listed back with the line number and the specific reason.

Files are decoded as `utf-8-sig` and every field stripped, because that is what
Excel actually produces. The importer also catches duplicate serial numbers
*within the same file* — something the database's `UNIQUE` constraint cannot
catch on its own, because none of the rows have been inserted yet when the second
one is validated. *Verified:* tests 9, 9b, 9c, 9d, 9e.

Excel import is not built in — `csv` is in the standard library and `openpyxl` is
not — but the Import page documents the pandas equivalent, including two traps:
`to_sql(if_exists="replace")` **drops and recreates** the table, destroying the
primary key, foreign keys and CHECK constraints; and `to_sql` performs no
validation at all, so pandas will happily write a row the application's own form
would have rejected.

### 7.7 End-to-end workflow

Verified against the shipped database; every figure below was produced by
actually running it. Step-by-step demo version: `documentation/DEMO_SCRIPT.md`.

| Step | Action | Database effect | Observed result |
|---|---|---|---|
| 1 | Open the dashboard | `SELECT` aggregates | **5 equipment · 10 repairs · 11 services · $4,381.20 · $2,014.75 · $6,395.95** |
| 2 | View the equipment register | `SELECT` + subqueries | 5 machines with per-machine costs |
| 3 | Register "Massey Ferguson 4707", serial `MF4707J2204410` | `INSERT` | Equipment count **6** |
| 4 | Open the new machine | 3-table read | Repairs **0** · Services **0** · Lifetime **$0.00** |
| 5 | Log a repair: hydraulic remote leak, Marcy Olsen, **$385.00** | `INSERT` with FK | Repairs total **$4,766.20** |
| 6 | Log a service: Oil Change, **$155.00**, next due 2027-03-03 | `INSERT` with FK | Maintenance total **$2,169.75** |
| 7 | View the machine's history | `JOIN` + `LEFT JOIN` + roll-ups | 1 repair · 1 service · **lifetime $540.00** · next service Mar 3, 2027 |
| 8 | Edit the repair to **$410.00** | `UPDATE` | Still 1 repair; **lifetime $565.00** |
| 9 | Open Reports | `GROUP BY` + aggregates | Lifetime cost by machine: Case IH **$2,851.00** → Massey Ferguson **$565.00** |
| 10 | Spending by mechanic | `LEFT JOIN` + `GROUP BY` + `COALESCE` | Dale Hutchins $2,152.15 · Marcy Olsen $1,618.25 · Travis Boyd $852.60 · **In-house $168.20** |
| 11 | Delete the new machine | `DELETE` + cascade | *"along with 1 repair(s) and 1 service record(s)"* |
| 12 | Back to the dashboard | aggregates re-run | **5 · 10 · 11 · $6,395.95** — exactly the starting state |
| 13 | `PRAGMA foreign_key_check` | integrity check | **clean** |

Nothing in that sequence is cached. Step 12 returns to step 1's numbers because
the database is the only source of truth.

---

## 8. Testing and Debugging

Full detail: **`documentation/TESTING.md`** and **`documentation/DEBUGGING.md`**.

### 8.1 Test approach

`python -m pytest tests/ -v` → **65 passed in 1.43s.**

Each test builds a fresh throwaway database in a temporary directory from
`schema.sql` + `sample_data.sql`, so the suite never touches `farmfix.db` and
every test starts from the same known state. Assertions are made through a
**separate raw connection**, so a page that looks right but wrote nothing cannot
pass.

### 8.2 The three test cases the assignment requires

| # | Input / action | Expected | Actual | Result |
|---|---|---|---|---|
| **1 — Add Equipment** | Valid tractor: Fendt 724 Vario, 2023, serial `TEST1SERIAL0001` | Inserted into SQLite and displayed | Count 5 → 6; every column stored as submitted; name appears on `/equipment` | **PASS** |
| **2 — Add Repair** | Repair on equipment 2 with mechanic 1, $212.50 | Saved with correct foreign key, visible in that machine's history | Count 10 → 11; `equipment_id = 2`, `mechanic_id = 1`, `cost = 212.5`; appears on `/equipment/2` and **not** on `/equipment/1` | **PASS** |
| **3 — SQL report** | Run the equipment repair-cost report (`LEFT JOIN` + `GROUP BY` + `SUM`) | Correct totals | All five per-machine totals matched a Python recomputation; they sum to **$4,381.20** = `SELECT SUM(cost) FROM repairs`; a machine with no repairs still appeared at $0.00 | **PASS** |

### 8.3 Additional cases

Twenty-eight further parametrised validation cases (invalid equipment, invalid
repair, invalid maintenance), `UPDATE` and `DELETE`, `ON DELETE CASCADE`,
`ON DELETE SET NULL`, foreign-key enforcement with and without the PRAGMA,
`CHECK` and `UNIQUE` enforcement, filtering, sorting, injection attempts, five
CSV-import cases, all sixteen pages rendering, and schema inspection. Full table
in `TESTING.md`.

**Four cases failed on their first run** and are recorded as failures:

| Case | What failed | Outcome |
|---|---|---|
| 8c | Searching for `%` returned all 5 machines | Fixed — bug 1 |
| 8d | Repair dated `2099-01-01` was accepted | Fixed — bug 3 |
| 8e | Cost `$1,240.75` was rejected | Fixed — bug 4 |
| M-6 | Two-join cost report was 2–3× too high | Fixed — bug 2 |

### 8.4 Debugging experience

Four real defects, documented in full in `DEBUGGING.md` with symptom, hypothesis,
investigation, fix, retest and result. The headline one:

**Problem.** The equipment search box returned every machine when the user typed
`%` or `_`.

**Error / behaviour.** None. No exception, nothing in the log, HTTP 200. The page
rendered perfectly and reported "5 machines" — it just reported the wrong five.

**Likely cause.** `%` and `_` are `LIKE` wildcards. `f"%{search}%"` with
`search = "%"` builds `'%%%'`, which matches everything. The bound parameter was
protecting the SQL *statement* correctly; nothing was protecting the *pattern*.

**Investigation.** Found by deliberately probing the search box rather than using
it normally. We confirmed the statement itself was safe (`' OR 1=1 --` returned
0 rows), which isolated the problem to the pattern. We then confirmed it was not
hypothetical: machinery model codes and serial numbers genuinely contain
underscores, so searching for model `X_200` would return the whole fleet.

**Solution.** Escape `%`, `_` and the backslash itself in the term — backslash
first, or the escapes added for the wildcards get doubled — and add `ESCAPE '\'`
to every `LIKE` clause. Applied to both search boxes.

**Retest.** All four wildcards went from 5 matches to 0, while `5075` still
returns 1, `1LV5075` returns 1 and `Deere` returns 2. Regression test
`test_08c_search_treats_percent_and_underscore_literally` also inserts a machine
whose model contains a literal underscore and asserts that searching for it
returns exactly one row. It fails against the old code. Full suite afterwards:
65 passed.

**Final result.** Fixed.

**What the four bugs had in common:** not one produced an error message. Every
one was valid SQL or valid Python that ran cleanly and gave a wrong answer.
Three were found by deliberately using the application *badly*; the fourth by
adding the numbers up and finding they did not reconcile.

---

## 9. AI Reflection

### 9.1 What AI was genuinely useful for

- **Learning the SQLite-specific rules quickly.** The PRAGMA behaviour, type
  affinity, the absence of a DATE type, `INTEGER PRIMARY KEY` versus
  `AUTOINCREMENT` — things you either already know or lose an evening to.
  Having them explained in the context of our own schema was the biggest time
  saving in the project.
- **Explaining *why*, not just *what*.** Asking "why can't I write `ORDER BY ?`
  when `WHERE x = ?` works?" produced the values-versus-identifiers distinction,
  which is now a concept we own rather than a rule we copied.
- **Framing design decisions as questions.** The best answer we got all project
  was not a snippet: it was "for each foreign key, ask what the child record
  means if its parent disappears." That question produced three different
  `ON DELETE` rules and is the part of the schema we are most confident
  defending.
- **First drafts of boilerplate** — Jinja templates, the request/teardown
  pattern, the CSV reader — which we then read and adjusted.

### 9.2 What needed human verification — and why

Everything whose output was *plausible*. The AI's answers were equally confident
when right and when wrong, so confidence carried no information at all. Three
categories recurred:

1. **Valid SQL that returns the wrong rows.** The two-join cost report ran
   without error and produced numbers that looked reasonable. Only reconciling
   against `SELECT SUM(cost) FROM repairs` revealed it was 200–300 % too high.
2. **Advice that is true but too narrow.** "It's parameterised, so it's safe"
   was correct about injection and silently wrong about LIKE patterns.
3. **Validation that checks shape instead of meaning.** The date-format regex
   was exactly what we asked for and let `2099-01-01` through.

None of these produces an error message. **The failures that matter are the
silent ones**, and the only defence is checking the result against something
independent — a hand-computed total, a second implementation, or a test written
specifically to fail against the wrong version.

### 9.3 One suggestion that needed correction

Detailed in §4.5(a): the AI's lifetime-cost query joined both child tables at
once and tripled every total, with `COUNT(DISTINCT ...)` keeping the counts
correct beside the inflated sums so that the report looked internally
consistent. It is the best example we have, because nothing about the code looks
wrong — it is the standard shape, it is what we asked for, and the one piece of
apparent extra care in it is precisely what hid the error.

### 9.4 What we learned about responsible AI-assisted development

1. **Verification is the work.** Generating a query took seconds; establishing
   that it returned the right rows took most of an evening and produced all the
   real learning. AI moved the effort from typing to checking — it did not
   remove it.
2. **Reconcile, don't eyeball.** Three of our four bugs were invisible to
   inspection and obvious the moment we added the numbers up and compared them
   to a total computed another way.
3. **Write the test that fails against the wrong answer.** A test that passes
   both before and after a change has verified nothing. Our most valuable test
   asserts what the *broken* query produced ($2,982.90) as well as what the
   correct one produces ($994.30), so the mistake cannot be reintroduced.
4. **Try to break your own application.** Typing `%` into a search box, a year
   with a slipped digit, a figure pasted off an invoice. Using the app correctly
   found nothing; using it badly found three defects in twenty minutes.
5. **The AI answers the question asked, not the question meant.** Most of our
   corrections traced back to an incomplete prompt rather than a wrong answer.
   Being specific about context is a skill, and it is the one that improved most
   over this project.
6. **You have to be able to explain it.** We chose raw SQL over an ORM partly so
   that every statement can be read aloud and defended on camera. Code nobody on
   the team can explain is a liability regardless of who or what wrote it.
7. **Say what the AI got wrong.** It would have been easy to present a clean
   record. The two documented AI errors are the most instructive part of this
   report, and pretending they did not happen would have thrown away the lesson.

---

## 10. Individual Contributions

> **TO BE COMPLETED BY EACH TEAM MEMBER BEFORE SUBMISSION.**
> Do not submit with these placeholders in place. Write what you actually did.

### Ayush Gaire

```
[ENTER ACTUAL CONTRIBUTION]

Suggested things to cover:
- Which parts of the database design / UML you worked on
- Which application features or pages you built or tested
- Which documentation sections you wrote
- Anything you debugged or verified
```

### Ashish Gaire

```
[ENTER ACTUAL CONTRIBUTION]

Suggested things to cover:
- Which parts of the database design / UML you worked on
- Which application features or pages you built or tested
- Which documentation sections you wrote
- Anything you debugged or verified
```

### AJ Rayamajhi

```
[ENTER ACTUAL CONTRIBUTION]

Suggested things to cover:
- Which parts of the database design / UML you worked on
- Which application features or pages you built or tested
- Which documentation sections you wrote
- Anything you debugged or verified
```

---

## 10b. Individual Reflection

> **ONE IMPORTANT THING EACH PERSON LEARNED. Written by that person.**

**Ayush Gaire:**

```
[Write one important thing you learned.]
```

**Ashish Gaire:**

```
[Write one important thing you learned.]
```

**AJ Rayamajhi:**

```
[Write one important thing you learned.]
```

---

## 11. Demo Video Link

```
[PASTE ZOOM LINK]
```

Length: 3–5 minutes. Script and speaking assignments:
`documentation/DEMO_SCRIPT.md`.

---

## Appendix — File map

| Deliverable | Location |
|---|---|
| Working application | `app.py` + `templates/` + `static/` |
| SQLite3 database file | `database/farmfix.db` |
| SQL schema | `database/schema.sql` |
| Sample data | `database/sample_data.sql` |
| Database build script | `database/init_db.py` |
| Sample CSVs | `data/sample_equipment.csv`, `data/sample_equipment_with_errors.csv` |
| UML class diagram | `uml/uml-diagram.png` · `.pdf` · `.svg` · `.html` |
| UML source | `uml/uml-diagram.mmd` (Mermaid), `uml/uml-source.md` (Mermaid + PlantUML) |
| UML → relational mapping | `documentation/UML_MAPPING.md` |
| AI learning evidence | `documentation/AI_LEARNING_EVIDENCE.md` |
| Testing documentation | `documentation/TESTING.md` |
| Debugging documentation | `documentation/DEBUGGING.md` |
| Demo script | `documentation/DEMO_SCRIPT.md` |
| D2L discussion post | `documentation/D2L_DISCUSSION.md` |
| Requirement checklist | `documentation/FINAL_CHECKLIST.md` |
| Test suite | `tests/test_app.py` |
| Setup and run instructions | `README.md` |
