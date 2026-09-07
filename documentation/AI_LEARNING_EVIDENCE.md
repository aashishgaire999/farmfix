# AI-Assisted SQLite3 Learning — Evidence

**FarmFix · COMP 368 Database Systems, Project 1**
Ayush Gaire · Ashish Gaire · AJ Rayamajhi

> **What this document is.** These are the AI-assisted decisions that actually
> shaped the code in this repository. Every "How we verified it" section points
> at a file, a test, or a command you can run right now to reproduce the check —
> nothing is described as verified unless it was. Interactions **2 and 3** are
> the required examples of the AI getting things **wrong**; both were real
> defects, and both fixes plus their regression tests are in the repo.
>
> **Team: add your own sessions in section 7** if you asked the AI something
> not captured here. Do not delete these — they are the ones tied to code.

---

## Contents

| # | Topic | Outcome |
|---|---|---|
| 1 | Foreign keys that look enforced but are not | AI **correct** — and we proved it with a negative test |
| 2 | **AI's cost query tripled every total** | AI **wrong** — real numbers, real fix |
| 3 | **AI's search box matched everything** | AI **wrong** — found by probing, not by using it |
| 4 | Choosing `CASCADE` vs `SET NULL` vs `RESTRICT` | AI **correct**, and it changed the design |
| 5 | Dates when SQLite has no DATE type | AI correct, but **incomplete** — we found the gap |
| 6 | Sorting by a column the user picks | AI **correct**, prevented a security mistake |

---

## Interaction 1 — "My foreign key isn't doing anything"

### Prompt

> "I wrote `FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id)` in my
> CREATE TABLE, but SQLite still lets me insert a repair with
> `equipment_id = 9999` when there is no machine 9999. Is my foreign key wrong?"

### AI response summary

The `FOREIGN KEY` clause was syntactically fine. The problem is SQLite-specific:
**foreign key enforcement is off by default**, for backwards compatibility with
databases created before SQLite supported it. It must be switched on with

```sql
PRAGMA foreign_keys = ON;
```

and — the part that mattered most — the setting lives on the **connection**, not
in the database file. Every new connection starts with it off again. The AI also
pointed us at `PRAGMA foreign_key_check`, which lists rows that violate a foreign
key, including orphans inserted while enforcement was off.

### What we learned

1. A *declared* constraint and an *enforced* constraint are two different things.
   This is unique to SQLite — in MySQL or PostgreSQL, declaring a foreign key is
   enough.
2. Because it is per connection, the PRAGMA has to be issued in *every* place
   that opens the database, not once at setup.
3. This makes application-side validation load-bearing in SQLite in a way it
   would not be on a stricter DBMS.

### What we implemented

`PRAGMA foreign_keys = ON` in all three places that open the database:

- `app.py`, in `get_db()` — runs on every web request;
- `database/init_db.py` — when the database is built;
- `tests/test_app.py`, in the `db_path` and `raw` fixtures.

`init_db.py` also runs `PRAGMA foreign_key_check` at the end and prints the
result, and the **Schema** page shows `PRAGMA foreign_keys` live, so you can see
it is `ON` during the demo.

### How we verified it

We did not take the AI's word for it. We wrote a test that proves the *bad*
behaviour still happens without the PRAGMA:

```python
def test_07_foreign_keys_are_enforced(raw):
    with pytest.raises(sqlite3.IntegrityError):
        raw.execute("INSERT INTO repairs (equipment_id, ...) VALUES (9999, ...)")

def test_07b_foreign_keys_off_would_allow_the_orphan(db_path):
    conn = sqlite3.connect(db_path)          # deliberately NO pragma
    conn.execute("INSERT INTO repairs (equipment_id, ...) VALUES (9999, ...)")
    conn.commit()
    assert conn.execute("PRAGMA foreign_key_check;").fetchall()   # orphan found
```

Both pass. The second is the proof: **identical schema, identical INSERT,
different result depending only on whether the PRAGMA was issued.**

---

## Interaction 2 — **The AI's cost report tripled every total** *(AI wrong)*

This is the interaction the assignment asks for: a suggestion that was plausible,
ran without error, and was wrong.

### Prompt

> "I have an `equipment` table and two child tables, `repairs` and
> `maintenance`, both with an `equipment_id` foreign key. Write me one query
> that shows, per machine: number of repairs, total repair cost, number of
> services, total service cost, and the two costs added together."

### AI response summary

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

It even used `COUNT(DISTINCT ...)`, which looks like careful, defensive SQL.

### What was wrong

Joining **two independent child tables** to the same parent produces the *cross
product* of the children. A machine with 3 repairs and 3 services yields
3 × 3 = 9 rows, so every repair cost is counted three times and every service
cost three times.

`COUNT(DISTINCT ...)` de-duplicates the **counts**, so those stay correct — which
makes the report look internally consistent while the sums beside them are
200–300 % too high. The `DISTINCT` the AI added is exactly what stops you
noticing.

Measured against our own data:

| Machine | True repair total | AI query's repair total | Rows the join produced |
|---|---|---|---|
| John Deere 5075E | **$994.30** | $2,982.90 | 9 (3 × 3) |
| Kubota L3902 | **$483.00** | $966.00 | 4 (2 × 2) |
| Case IH Axial-Flow 6150 | **$2,021.00** | $4,042.00 | 4 |
| John Deere 1775NT | **$512.60** | $1,025.20 | 2 (1 × 2) |
| New Holland BR7060 | **$370.30** | $740.60 | 4 |

The multiplier is different for every machine, so the *ranking* is not even
consistently wrong — which is why eyeballing the report does not catch it.

### What we learned

- A `JOIN` does not just fetch related data, it **changes the number of rows**,
  and every aggregate downstream is computed over that changed set.
- One parent + one child in a query is safe. One parent + two independent
  children is not.
- `SUM(DISTINCT cost)` is not the fix and is actively worse: two repairs that
  each cost exactly $55.00 would collapse into one and the total would be too
  *low* — an invisible under-count instead of a visible over-count.

### What we implemented

A **correlated subquery per total**, so each table is aggregated independently
and nothing multiplies (`app.py`, `REPORTS["cost_by_equipment"]`):

```sql
SELECT e.name AS label,
       (SELECT COALESCE(SUM(r.cost),0) FROM repairs r
         WHERE r.equipment_id = e.equipment_id) AS repair_total,
       (SELECT COALESCE(SUM(m.cost),0) FROM maintenance m
         WHERE m.equipment_id = e.equipment_id) AS service_total,
       ...
FROM equipment e
ORDER BY total DESC;
```

The same pattern is used for the cost columns on the equipment list page. The
single-table reports still use a plain `LEFT JOIN` + `GROUP BY`, which is
correct — the problem only appears with two child tables in one query.

### How we verified it

1. **Computed the totals twice, two different ways**, and compared — once with
   the join, once one table at a time. The numbers in the table above are the
   actual recorded output.
2. **Reconciled against the whole table.** The five lifetime totals sum to
   $6,395.95, which equals
   `SUM(repairs.cost) + SUM(maintenance.cost)` = $4,381.20 + $2,014.75.
3. **Wrote a regression test that pins the wrong answer too** —
   `test_03b_lifetime_cost_is_not_inflated_by_a_double_join` asserts the
   application's query matches the truth for all five machines *and* asserts
   that the naive version really does produce $2,982.90 where the truth is
   $994.30. That second assertion exists so nobody "simplifies" the query back.

Full write-up: `documentation/DEBUGGING.md`, bug 2.

---

## Interaction 3 — **The AI's search box matched everything** *(AI wrong)*

A second real defect, of a different kind: not a wrong result set, but user
input being read as code.

### Prompt

> "Add a search box to the equipment page that looks across name, manufacturer,
> model and serial number in one query."

### AI response summary

```python
where.append("(e.name LIKE ? OR e.manufacturer LIKE ? "
             "OR e.model LIKE ? OR e.serial_number LIKE ?)")
params.extend([f"%{search}%"] * 4)
```

The AI noted — correctly — that the search term is passed as a bound `?`
parameter, so this is not vulnerable to SQL injection.

### What was wrong

The advice was true and the conclusion was too narrow. A bound parameter protects
the SQL **statement**; it does not stop the value from being interpreted as a
**LIKE pattern** once it arrives. `%` means "any sequence of characters" and `_`
means "any single character", so:

- searching for `%` builds the pattern `'%%%'` → matches **every** row;
- searching for `_` builds `'%_%'` → "any string with at least one character" →
  also every row.

We confirmed this is not hypothetical: machinery model codes and serial numbers
genuinely contain underscores. A user searching for model `X_200` would get back
every machine on the farm.

### What we learned

"Parameterised, therefore safe" is a half-truth. Parameters solve injection.
They do not solve **input that is syntax in some other language** — LIKE
patterns here, and the same idea applies to regular expressions and glob
patterns. The escaping has to happen at the level of the pattern, not the
statement.

### What we implemented

```python
def like_term(text):
    escaped = (str(text).replace("\\", "\\\\")
                        .replace("%", "\\%").replace("_", "\\_"))
    return f"%{escaped}%"
```

```sql
(e.name LIKE ? ESCAPE '\' OR e.manufacturer LIKE ? ESCAPE '\' ...)
```

The backslash must be escaped **first**, or the backslashes added for `%` and
`_` would be doubled by the later replacement. The same fix was applied to the
repairs search.

### How we verified it

Before:

```
   equipment search '%'    -> 5 matched      (all of them)
   equipment search '_'    -> 5 matched
```

After:

```
   equipment search '%'        -> 0 matched
   equipment search '_'        -> 0 matched
   equipment search '5075'     -> 1 matched
   equipment search '1LV5075'  -> 1 matched
   equipment search 'Deere'    -> 2 matched
```

`test_08c_search_treats_percent_and_underscore_literally` asserts each wildcard
returns zero matches, then inserts a machine whose model genuinely contains an
underscore (`X_200`) and asserts searching for it returns **exactly one** row.
It fails against the old code.

We also confirmed the AI's original claim was still true: searching `' OR 1=1 --`
returns 0 rows, so the statement itself was never at risk.

---

## Interaction 4 — Choosing between CASCADE, SET NULL and RESTRICT

### Prompt

> "What should `ON DELETE` be for each foreign key? I have repairs pointing at
> equipment, maintenance pointing at equipment, and repairs pointing at
> mechanics."

### AI response summary

The AI explained the four options (`CASCADE`, `SET NULL`, `RESTRICT`,
`NO ACTION`) and gave the question to ask for each foreign key: *what does this
child record mean if its parent disappears?* It suggested `CASCADE` for the
equipment relationships and `SET NULL` for the mechanic one, and explained why
they differ.

### What we learned

The delete rule is a **modelling decision, not a technical default**, and the
three foreign keys in this schema genuinely want different answers:

| Foreign key | Action | Why |
|---|---|---|
| `repairs.equipment_id` | `CASCADE` | A repair is *owned* by a machine. Scrap the machine and the history has no subject. |
| `maintenance.equipment_id` | `CASCADE` | Same reasoning. |
| `repairs.mechanic_id` | `SET NULL` | A mechanic merely *performed* the work. Removing them from the contact list must not erase the fact that the repair happened and cost $615.40. |

We also learned that `SET NULL` is only possible because `mechanic_id` is
nullable — which is the same design decision as the `0..1` multiplicity in the
UML, arrived at from the other direction.

### What we implemented

Exactly the table above, in `database/schema.sql`. The Schema page displays each
`on_delete` value live from `PRAGMA foreign_key_list`, and the delete
confirmation dialogs tell the user which behaviour they are about to trigger.

### How we verified it

Three separate tests, because three different behaviours:

- `test_06b_delete_equipment_cascades` — deleting machine 5 removes its 2 repairs
  and 2 service records, and `PRAGMA foreign_key_check` stays clean.
- `test_06c_delete_mechanic_sets_null_and_keeps_the_repairs` — deleting mechanic
  1 **keeps** the repair rows (total row count unchanged), sets their
  `mechanic_id` to `NULL`, and they then display as in-house.
- `test_11_schema_inspection` asserts the declared actions are exactly
  `{(equipment_id, equipment, CASCADE), (mechanic_id, mechanics, SET NULL)}`, so
  a future edit to the schema cannot silently change them.

---

## Interaction 5 — Dates, when SQLite has no DATE type *(correct but incomplete)*

### Prompt

> "What column type should `repair_date` and `next_service_date` be, and how do
> I group repairs by month?"

### AI response summary

SQLite has **no DATE or DATETIME type**. Its five storage classes are `NULL`,
`INTEGER`, `REAL`, `TEXT` and `BLOB`. Dates are conventionally stored as ISO-8601
`TEXT` (`'2026-09-04'`), because that format sorts chronologically as plain text
and works with SQLite's date functions:

```sql
GROUP BY strftime('%Y-%m', repair_date)
```

The AI warned that this only works if the stored strings really are
ISO-formatted: `'09/04/2026'` returns `NULL` from `strftime`, and the row
silently disappears from a grouped report rather than raising an error. It
recommended validating the format in the application.

### What we learned

- The declared "type" in SQLite is a *type affinity* — a preference, not a rule.
  SQLite will store a string in a column declared `INTEGER` if asked.
- Comparing ISO date strings with `<` and `>` is correct and is how the overdue
  check works.
- **What the AI did not say, and we found ourselves:** validating the *format* is
  not the same as validating the *value*. `'2099-01-01'` and `'1899-01-01'` both
  match `YYYY-MM-DD` perfectly and are both obviously typing mistakes. We
  discovered this by probing the form with a slipped digit, and both were
  accepted.

### What we implemented

- `repair_date`, `service_date`, `purchase_date`, `next_service_date` all
  `TEXT`, always written as ISO.
- HTML `<input type="date">`, which submits ISO natively.
- `strftime('%Y-%m', ...)` for the repairs-by-month report.
- A shared `check_date()` helper that validates format **and** range, with an
  `allow_future` flag — because `next_service_date` is the one date in the
  schema where the future is correct:

```python
if value < EARLIEST_DATE:                       # '1900-01-01'
    errors.append(f"{label} '{value}' is before 1900 — check the year")
elif not allow_future and value > date.today().isoformat():
    errors.append(f"{label} '{value}' is in the future")
```

- `next_service_date` stored as `NULL`, never `''`, when nothing is scheduled —
  because `'' <= '2026-10-19'` is **true**, so a blank string would show up as
  permanently overdue.

### How we verified it

- `test_08d_implausible_dates_are_rejected` covers 1899 and 2099 **and** asserts
  a `next_service_date` of `2027-03-03` is still accepted, so the fix did not
  break scheduling.
- `test_04b_maintenance_without_next_date_is_null_not_empty` asserts a blank form
  field becomes `None`, not `''`.
- `test_08b_overdue_filter_excludes_null_next_dates` asserts the overdue set and
  the not-scheduled set never overlap.
- The monthly report reconciles: 1+1+2+1+2+2+1 = 10 repairs, and
  $296.00 + $615.40 + $940.60 + $38.90 + $835.25 + $1,315.05 + $340.00 =
  $4,381.20, which equals `SELECT SUM(cost) FROM repairs` — so no row was
  dropped by a `strftime` returning `NULL`.

---

## Interaction 6 — Sorting by a column the user picks

### Prompt

> "The user clicks a column heading to choose the sort order. Can I pass the
> column name as a `?` parameter like I do with values?"

### AI response summary

No. Bound parameters substitute **values**, not **identifiers**. `ORDER BY ?`
sorts every row by the same constant string, which silently does nothing. And
building the SQL with an f-string —

```python
sql = f"SELECT ... ORDER BY {request.args.get('sort')}"   # DO NOT DO THIS
```

— pastes user input straight into the statement, which *is* SQL injection. The
AI recommended a **whitelist**: map the user's key through a dictionary the
programmer controls, with a default for anything unrecognised.

### What we learned

The values-versus-identifiers distinction is what makes "just use parameters
everywhere" insufficient advice. Table names, column names and `ASC`/`DESC` all
have to be validated against a fixed set instead. (Interaction 3 turned out to be
a third category: a value that is *pattern syntax*.)

### What we implemented

Three whitelists in `app.py` — `EQUIPMENT_SORTS`, `REPAIR_SORTS`,
`MAINTENANCE_SORTS`:

```python
REPAIR_SORTS = {
    "date": "r.repair_date", "cost": "r.cost", "equipment": "e.name",
    "mechanic": "mechanic_name", "problem": "r.problem",
}
...
order_sql = f"ORDER BY {REPAIR_SORTS.get(sort, 'r.repair_date')} {direction}"
```

`direction` is reduced to exactly `"ASC"` or `"DESC"` before use. Every *value*
in every `WHERE` clause is still a bound `?` parameter.

### How we verified it

`test_08_filter_and_sort` sends a hostile sort key to two different pages and
then checks the tables are still there:

```python
assert client.get("/repairs?sort=1;DROP TABLE repairs--").status_code == 200
assert count(raw, "repairs") == SEED_REPAIRS
assert client.get("/equipment?sort=1;DROP TABLE equipment--").status_code == 200
assert count(raw, "equipment") == SEED_EQUIPMENT
```

The unrecognised key falls back to the default column and never reaches the SQL.
The same test also asserts that a descending sort really is descending.

---

## Summary: what needed human verification

| The AI was reliable at | The AI needed checking on |
|---|---|
| Explaining SQLite's own rules (PRAGMA, type affinity, no DATE type) | Whether a query returned the **right rows**, not just valid rows |
| Producing syntactically valid SQL first time | Anything depending on a requirement we had not stated |
| Security advice when we asked for it directly | Security problems we did not think to ask about |
| Suggesting the standard, idiomatic approach | Whether the standard approach fits *this* data shape |

The pattern across all six: **the AI's answers were equally confident when right
and when wrong**, so confidence carried no information at all. Interaction 2 is
the clearest case — the AI added `COUNT(DISTINCT ...)`, which reads as extra
care, and that very addition is what hid the error.

Every one of these was checked against the actual database: by adding the
numbers up by hand, by computing the same figure a second way, or by writing a
test that fails against the wrong version. **That verification step, not the AI,
is what makes the code in this repository trustworthy.**

---

## 7. Team additions

*Add any AI sessions of your own below, using the same five headings:
Prompt · AI Response Summary · What We Learned · What We Implemented ·
How We Verified It.*

### Interaction 7 — [Ayush Gaire]

*[Add here if you have one.]*

### Interaction 8 — [Ashish Gaire]

*[Add here if you have one.]*

### Interaction 9 — [AJ Rayamajhi]

*[Add here if you have one.]*
