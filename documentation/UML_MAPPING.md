# UML → Relational Mapping

**FarmFix · COMP 368 Database Systems, Project 1**
Ayush Gaire · Ashish Gaire · AJ Rayamajhi

This document explains how the UML class diagram in `uml/uml-diagram.png` became
the SQLite3 schema in `database/schema.sql`, and **why** each decision was made.
The rules applied are the standard conceptual-to-logical mapping rules.

---

## 1. The mapping rules

| UML construct | Relational construct | Applied here |
|---|---|---|
| Class | Table | 4 classes → 4 tables |
| Attribute | Column with a SQLite type affinity | `cost : Real` → `cost REAL` |
| Identifier («PK») | `PRIMARY KEY` | `equipment_id`, `repair_id`, `maintenance_id`, `mechanic_id` |
| One-to-many association | Foreign key column on the **many** side | `repairs.equipment_id`, `maintenance.equipment_id`, `repairs.mechanic_id` |
| Multiplicity `1` on the parent side | `NOT NULL` on the child's foreign key | `equipment_id` on both children |
| Multiplicity `0..1` on the parent side | **Nullable** foreign key | `repairs.mechanic_id` |
| Multiplicity `0..*` | No constraint — zero rows is simply zero rows | a new machine legitimately has no repairs |
| Many-to-many association | Junction table | **not needed here** — see §4 |
| Business uniqueness rule | `UNIQUE` constraint | `equipment.serial_number` |
| Restricted value list | `CHECK (... IN (...))` | `equipment_type`, `status`, `service_type` |

---

## 2. Class → Table, one at a time

### 2.1 `Equipment` → `equipment`

```sql
CREATE TABLE equipment (
    equipment_id   INTEGER PRIMARY KEY,
    name           TEXT    NOT NULL,
    equipment_type TEXT    NOT NULL DEFAULT 'Tractor'
                   CHECK (equipment_type IN ('Tractor','Combine','Planter',
                          'Sprayer','Baler','Tillage','Loader','Truck',
                          'Irrigation','Other')),
    manufacturer   TEXT    NOT NULL,
    model          TEXT,
    year           INTEGER CHECK (year BETWEEN 1900 AND 2100),
    serial_number  TEXT    UNIQUE,
    purchase_date  TEXT,
    status         TEXT    NOT NULL DEFAULT 'Operational'
                   CHECK (status IN ('Operational','Needs Repair','In Repair',
                          'Out of Service','Retired'))
);
```

| UML attribute | Column | Type | Why |
|---|---|---|---|
| `equipment_id` «PK» | `equipment_id` | `INTEGER PRIMARY KEY` | In SQLite this is an alias for the internal `rowid`, so it auto-increments on its own. `AUTOINCREMENT` is unnecessary here — it only adds a bookkeeping table, and is needed only when ids must never be reused. |
| `name` | `name` | `TEXT NOT NULL` | What the farmer actually calls the machine. A machine with no name cannot be picked from a dropdown. |
| `equipment_type` | `equipment_type` | `TEXT` + `CHECK ... IN` | SQLite has no `ENUM` type. A `CHECK` with an `IN` list is the equivalent, and it makes the database — not just the Python — reject "Spaceship". |
| `manufacturer`, `model` | `TEXT` | | `manufacturer` is `NOT NULL` because you always know the make; `model` is nullable because on an old machine you sometimes do not. |
| `year` | `INTEGER` + `CHECK` | | Stored as a number so it can be sorted and compared. The `CHECK` catches a typo like `20199`. |
| `serial_number` | `TEXT UNIQUE` | | **The natural key.** It is stamped on the frame and is what a dealer asks for. `UNIQUE` stops the same machine being registered twice — which is a real risk on a farm where two people enter data. |
| `purchase_date` | `TEXT` | ISO `'YYYY-MM-DD'` | **SQLite has no DATE type.** ISO text sorts chronologically and works with `strftime()`. This is the officially recommended approach. |
| `status` | `TEXT` + `CHECK ... IN` | | Drives the colour coding on the dashboard, so the value set has to be closed. |

**Why a surrogate key when `serial_number` is unique?** Because serial numbers
get mistyped, and correcting one would mean rewriting every foreign key that
referenced it. An opaque `equipment_id` never changes.

### 2.2 `Mechanic` → `mechanics`

```sql
CREATE TABLE mechanics (
    mechanic_id INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    shop        TEXT,
    phone       TEXT,
    specialty   TEXT
);
```

**Why this table exists at all.** The obvious design puts a `mechanic_name` text
column straight on `repairs`. We rejected it: the same person then gets typed as
"Dale Hutchins", "Dale H." and "dale hutchins", and the *"repair spending by
mechanic"* report splits one mechanic into three rows that each look small.
Storing the name once and referencing it by id is the third-normal-form fix, and
it also gives somewhere to keep the phone number — which is what you actually
want at 6 a.m. during harvest.

It is a genuinely small table. We did **not** add tables for parts, invoices,
suppliers or hour meters, all of which a commercial system would have, because
they would not have taught anything the four tables do not already demonstrate.

### 2.3 `Repair` → `repairs` (two associations, two different rules)

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

**The `Equipment 1 → 0..* Repair` association.** The rule for a one-to-many
association is: **put the foreign key on the "many" side.** `Repair` is the many
side, so `repairs` carries `equipment_id`. No extra table is needed, and adding
one would be actively wrong — a junction table would allow one repair to belong
to two machines, which the multiplicity `1` explicitly forbids.

`equipment_id` is `NOT NULL` because the parent multiplicity is `1`, not `0..1`.
A repair belonging to no machine could never appear in a history or a cost
roll-up; it would be invisible money. `NOT NULL` turns that modelling decision
into something the database refuses to break.

**The `Mechanic 0..1 → 0..* Repair` association.** `mechanic_id` is
**nullable**, which is the direct translation of the `0..1` multiplicity. This
is the one place the real world pushed back on a tidier model: farmers fix a
great deal themselves, and three of the ten sample repairs (a retensioned belt,
a plugged tire, a spring from the parts bin) have no mechanic and no invoice.
Forcing a mechanic onto every repair would mean inventing a fake "Self" row,
which pollutes the mechanic list and distorts every per-mechanic report. `NULL`
says exactly what is true: *no mechanic on record.*

**Why three different `ON DELETE` behaviours across the schema.** This is the
most interesting design decision in the project, and each one answers a
different question — *what does this record mean if its parent disappears?*

| Foreign key | Action | Reasoning |
|---|---|---|
| `repairs.equipment_id` | `CASCADE` | A repair is *owned* by a machine. Scrap the machine and its repair history has no subject. This is a composition. |
| `maintenance.equipment_id` | `CASCADE` | Same reasoning. |
| `repairs.mechanic_id` | `SET NULL` | A mechanic merely *performed* the work. Taking them out of the contact list must not erase the fact that the repair happened and cost $615.40 — that money still left the farm. The repair survives, showing as in-house. |

`CHECK (cost >= 0)` rather than `> 0`: a warranty repair genuinely costs
nothing, and recording it as $0.00 is more useful than not recording it.

### 2.4 `Maintenance` → `maintenance`

```sql
CREATE TABLE maintenance (
    maintenance_id    INTEGER PRIMARY KEY,
    equipment_id      INTEGER NOT NULL,
    service_date      TEXT    NOT NULL,
    service_type      TEXT    NOT NULL CHECK (service_type IN (...)),
    description       TEXT,
    cost              REAL    NOT NULL DEFAULT 0 CHECK (cost >= 0),
    next_service_date TEXT,                           -- NULL = none scheduled
    notes             TEXT,
    FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id) ON DELETE CASCADE
);
```

Structurally the same as `repairs`, with one column worth dwelling on.

**`next_service_date` is nullable, and the `NULL` means something specific.** A
one-off inspection does not always book a follow-up, so "no next service" is a
real state — and it is *not* the same as "due today" or "overdue". Every query
that touches this column has to say so explicitly:

```sql
WHERE m.next_service_date IS NOT NULL AND m.next_service_date <= ?
```

Leaving out the `IS NOT NULL` would be harmless in SQL (a `NULL` comparison is
never true) but the empty string would not be: `'' <= '2026-10-19'` is **true**,
so a blank stored instead of a `NULL` would show up as permanently overdue.
That is why `validate_maintenance()` converts an empty form field to `None`
rather than `''`, and why `test_04b` asserts on it specifically.

**Why repairs and maintenance are two tables and not one.** They look similar —
both are "something that happened to a machine on a date and cost money" — and a
single `service_events` table with a `kind` column would work. We kept them
separate because their *attributes genuinely differ*: a repair has a `problem`
(something broke) and a mechanic; a service has a `service_type` and a
`next_service_date` (something scheduled). Merging them would leave half the
columns `NULL` on every row and make the `CHECK` constraints impossible to
write. The distinction is also the one a farmer cares about: high service cost
is planned spending, high repair cost is not.

---

## 3. Indexes

```sql
CREATE INDEX idx_repairs_equipment     ON repairs(equipment_id);
CREATE INDEX idx_repairs_mechanic      ON repairs(mechanic_id);
CREATE INDEX idx_repairs_date          ON repairs(repair_date);
CREATE INDEX idx_maintenance_equipment ON maintenance(equipment_id);
CREATE INDEX idx_maintenance_next      ON maintenance(next_service_date);
```

SQLite automatically indexes the primary key of every table and the columns of
every `UNIQUE` constraint. It does **not** automatically index the *child* side
of a foreign key — and every join and every filter in this application uses
exactly those columns, so they are indexed explicitly.
`PRAGMA index_list(<table>)` on the Schema page shows both these and the
automatic ones.

---

## 4. Why there is no junction table

Both core associations are one-to-many:

- one repair happens to one machine — not several;
- one service is performed on one machine — not several.

So the foreign key goes on the many side and nothing else is needed. **A
junction table is the correct answer to a many-to-many and the wrong answer to a
one-to-many**: adding one here would let a single repair belong to two tractors,
which is not true of the real world and would double-count that repair in every
cost report.

`Mechanic → Repair` might look like a candidate, but it is not either: a repair
has *at most one* mechanic, so a nullable foreign key is the right translation,
not a junction table.

If FarmFix were extended to track **parts**, a junction table would appear
immediately and naturally — one repair uses many parts, and one part number is
used in many repairs. That is a genuine many-to-many, and
`repair_parts(repair_id, part_id, quantity, unit_price)` would be the
association table. We left it out to keep the project at a size all three of us
can explain.

---

## 5. Summary tables

| UML class | SQLite table | Primary key | Foreign keys | Rows shipped |
|---|---|---|---|---|
| `Equipment` | `equipment` | `equipment_id` | — | 5 |
| `Mechanic` | `mechanics` | `mechanic_id` | — | 3 |
| `Repair` | `repairs` | `repair_id` | `equipment_id` → `equipment` (NOT NULL, CASCADE); `mechanic_id` → `mechanics` (nullable, SET NULL) | 10 |
| `Maintenance` | `maintenance` | `maintenance_id` | `equipment_id` → `equipment` (NOT NULL, CASCADE) | 11 |

| UML association | Multiplicity | Relational implementation |
|---|---|---|
| Equipment *has* Repair | `1` → `0..*` | `repairs.equipment_id`, NOT NULL FK, `ON DELETE CASCADE` |
| Equipment *receives* Maintenance | `1` → `0..*` | `maintenance.equipment_id`, NOT NULL FK, `ON DELETE CASCADE` |
| Mechanic *performs* Repair | `0..1` → `0..*` | `repairs.mechanic_id`, **nullable** FK, `ON DELETE SET NULL` |

| UML type | SQLite type | Note |
|---|---|---|
| `int` | `INTEGER` | |
| `String` | `TEXT` | |
| `Real` | `REAL` | floating point; see README limitation 3 |
| `Date` | `TEXT` | ISO `'YYYY-MM-DD'` — SQLite has no DATE type |
| `Boolean` | *(none stored)* | the `isOverdue()` / `isInHouse()` operations on the diagram are **derived**, computed by comparing dates or testing `mechanic_id IS NULL`. Storing them would let them go stale. |

---

## 6. Normalisation check

The schema is in **third normal form**:

- **1NF** — every column holds a single atomic value. There is no "repairs"
  column containing a comma-separated list, and no "parts used" free-text field
  pretending to be structured data.
- **2NF** — no partial dependency on part of a key. Every table has a single-
  column primary key, so the condition holds trivially.
- **3NF** — no transitive dependency. `repairs` stores `mechanic_id`, not
  `mechanic_name` or `mechanic_phone`. Correcting a phone number is a one-row
  `UPDATE` on `mechanics`; nothing in `repairs` changes, and the same mechanic
  can never appear under two spellings. This is precisely the problem §2.2
  describes, stated formally.
