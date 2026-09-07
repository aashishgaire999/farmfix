# Testing

**FarmFix · COMP 368 Database Systems, Project 1**
Ayush Gaire · Ashish Gaire · AJ Rayamajhi

---

## How to run the tests

From the project root:

```bash
python -m pytest tests/ -v
```

Every test builds a **fresh throwaway database** in a temporary directory from
`database/schema.sql` + `database/sample_data.sql` and points the Flask app at
it, so the suite never touches `database/farmfix.db`. That is why every test can
assume the same starting state:

| | Rows | Total cost |
|---|---|---|
| `equipment` | 5 | — |
| `mechanics` | 3 | — |
| `repairs` | 10 | $4,381.20 |
| `maintenance` | 11 | $2,014.75 |

**Actual result of the last full run:**

```
platform linux -- Python 3.11.15, pytest-9.1.1, pluggy-1.6.0
rootdir: /.../farmfix
collected 65 items
.................................................................  [100%]
65 passed in 1.43s
```

Every case below was run. The Pass/Fail column records what actually happened,
including the four cases that **failed on their first run** and had to be fixed.

---

## Automated test cases

### The three the assignment asks for

| # | Input or action | Expected result | Actual result | Pass/Fail | Notes |
|---|---|---|---|---|---|
| **1** | **Add Equipment.** POST valid tractor: "Fendt 724 Vario", Tractor, Fendt, 724 Vario, 2023, serial `TEST1SERIAL0001`, purchased 2023-04-11, Operational | Row inserted into SQLite and displayed in the register | `equipment` count rose 5 → 6. Row found with `name`, `manufacturer`, `year = 2023`, `equipment_type = 'Tractor'` all exactly as submitted. The name appears in the rendered `/equipment` page. | **PASS** | — |
| **2** | **Add Repair** against a valid foreign key: equipment 2 (Kubota L3902), mechanic 1 (Dale Hutchins), 2026-09-03, "PTO shaft guard cracked", $212.50 | Repair saved with the correct foreign key and visible in that machine's history — and **only** that machine's | `repairs` count rose 10 → 11. Stored row had `equipment_id = 2`, `mechanic_id = 1`, `cost = 212.5`. Appears on `/equipment/2`; **absent** from `/equipment/1`. | **PASS** | The "absent from the other machine" assertion is what actually proves the FK is doing the work |
| **3** | **SQL report.** Run the equipment repair-cost report (`LEFT JOIN` + `GROUP BY` + `SUM`) | JOIN/GROUP BY/SUM returns correct totals | All five per-machine totals matched the same figures computed row-by-row in Python. The five totals sum to **$4,381.20**, which equals `SELECT SUM(cost) FROM repairs`. A newly inserted machine with no repairs still appeared, with total `$0.00`. | **PASS** | The last assertion fails against an INNER JOIN version |

### Additional cases

| # | Input or action | Expected result | Actual result | Pass/Fail | Notes |
|---|---|---|---|---|---|
| **1b** | Eight invalid equipment submissions: blank name; blank manufacturer; type `Spaceship`; status `Broken Down`; year `nineteen`; year `1750`; date `04/11/2023`; serial `1LV5075EKKY123456` (already used) | Each rejected with a specific message; row count unchanged | All eight rejected with the expected message (`name is required`, `manufacturer is required`, `equipment type …`, `status …`, `not a whole number`, `between 1900 and 2100`, `YYYY-MM-DD`, `already registered`). Count stayed 5 every time. | **PASS** (8 cases) | — |
| **2b** | Add a repair with the mechanic dropdown left blank | Accepted, `mechanic_id` stored as `NULL`, still visible in history labelled in-house | Stored with `mechanic_id IS NULL`. Appears on `/equipment/1` and shows as "In-house" on `/repairs`. | **PASS** | This is the `0..1` multiplicity working |
| **2c** | Seven invalid repair submissions: blank equipment; equipment 9999; mechanic 9999; blank problem; date `09/03/2026`; cost `-40`; cost `free` | Each rejected; row count unchanged | All seven rejected with the expected message. Count stayed 10. | **PASS** (7 cases) | — |
| **3b** | **Double-JOIN regression.** Compare the app's lifetime-cost query against totals computed one table at a time, and against the naive two-LEFT-JOIN version | App's query matches the truth exactly; the naive version over-counts | App's query matched all five machines. Naive version returned **$2,982.90** for the John Deere 5075E where the truth is **$994.30** — exactly 3× because that machine has 3 service records. | **PASS** | Bug 2 in `DEBUGGING.md`. The test pins the *wrong* number too, so nobody re-simplifies the query |
| **4** | **Add Maintenance:** equipment 3, 2026-09-03, Oil Change, $168.40, next due 2027-03-03 | Inserted with correct FK and next date; visible on that machine's page | `maintenance` count rose 11 → 12. `equipment_id = 3`, `cost = 168.4`, `next_service_date = '2027-03-03'`. Visible on `/equipment/3`. | **PASS** | — |
| **4b** | Add a service record with the "next service due" field left blank | Stored as `NULL`, **not** the empty string | `next_service_date IS NULL`. The record appears under the "None scheduled (NULL)" filter. | **PASS** | `'' <= '2026-10-19'` is true, so a blank string would read as permanently overdue |
| **4c** | Five invalid service submissions: equipment 9999; type `Wash and wax`; date `03/09/2026`; next date before the service date; cost `-1` | Each rejected; row count unchanged | All five rejected with the expected message. Count stayed 11. | **PASS** (5 cases) | — |
| **5** | **UPDATE a repair:** change repair 1's cost to $777.77, its problem text, and its mechanic 1 → 2 | New values stored; **row count unchanged** (an UPDATE, not an INSERT) | `cost = 777.77`, new problem text, `mechanic_id = 2`. Count still 10. | **PASS** | The row-count assertion is what catches an accidental INSERT |
| **5b** | UPDATE equipment 3's status from "Needs Repair" to "Operational" | Status changes; count unchanged | Status `Operational`; count still 5. | **PASS** | — |
| **6** | **DELETE a repair** (repair 2) | Row gone; count 10 → 9 | `SELECT … WHERE repair_id = 2` returned `None`; count 9. | **PASS** | — |
| **6b** | **ON DELETE CASCADE:** delete equipment 5 (New Holland BR7060), which has 2 repairs and 2 service records | Machine **and** all four child rows removed; no orphans left | Machine row `None`. Repairs for machine 5: 0. Maintenance for machine 5: 0. `PRAGMA foreign_key_check` returned no rows. | **PASS** | — |
| **6c** | **ON DELETE SET NULL:** delete mechanic 1 (Dale Hutchins), who worked on 3 repairs | Mechanic removed, but the **repairs survive** with `mechanic_id = NULL` | Mechanic row `None`. `repairs` count **unchanged**. Repairs with `mechanic_id = 1`: 0. `foreign_key_check` clean. They now display as "In-house". | **PASS** | The contrast with 6b is the point: two child tables, two different delete rules |
| **6d** | Delete a repair from that repair's **own edit page** (with the `Referer` header a browser sends) | One success message; no contradictory second message | One message: *"Deleted repair #3 from the database."* No "no longer exists". | **PASS** | We wrote `_safe_back()` for this from the start rather than discovering it the hard way |
| **7** | Direct `INSERT` with `equipment_id = 9999` into `repairs`, then into `maintenance`, on a connection with `PRAGMA foreign_keys = ON` | Both raise `sqlite3.IntegrityError` | Both raised `IntegrityError: FOREIGN KEY constraint failed`. | **PASS** | — |
| **7b** | The **same** INSERT on a connection that never issues the PRAGMA | SQLite accepts the orphan; `PRAGMA foreign_key_check` then reports it | Insert accepted. `foreign_key_check` returned 1 row. | **PASS** | Deliberate negative test proving the PRAGMA, not the `FOREIGN KEY` clause alone, is what enforces |
| **7c** | Direct INSERTs violating `CHECK (cost >= 0)`, `CHECK (equipment_type IN …)`, and `UNIQUE (serial_number)` | All three raise `IntegrityError` | All three raised `IntegrityError`. | **PASS** | Proves the constraints are enforced at the database level, not only in Python |
| **8** | Filter repairs by machine, by in-house (`mechanic_id IS NULL`), and by an impossible minimum cost; search equipment by name fragment and by serial fragment; check descending sort; send `?sort=1;DROP TABLE repairs--` to two pages | Counts match direct SQL; empty state shown; injection ignored and both tables survive | Counts matched. Empty state rendered. Injection requests returned 200 and the row counts were still 10 and 5. Descending sort verified. | **PASS** | Sort keys go through a whitelist, never into the SQL string |
| **8b** | Filter maintenance by "overdue" | The overdue set and the "no next date" set must not overlap | Both sets non-empty and disjoint; the page count matched the direct SQL count. | **PASS** | — |
| **8c** | **Search for a literal `%`, `_`, `%%`, `_%`**; then search for a model that genuinely contains an underscore (`X_200`) | Wildcards match nothing; `X_200` matches exactly one machine | **First run: FAILED.** `%` and `_` each returned **all 5 machines**. After the fix: all four wildcards returned 0; `X_200` returned exactly 1; ordinary searches unchanged. | **FAIL → PASS after fix** | Bug 1 in `DEBUGGING.md` |
| **8d** | Add a repair dated `2099-01-01`, then `1899-01-01`; then add a service with `next_service_date = 2027-03-03` | Both bad dates rejected; the future *scheduled* date still accepted | **First run: FAILED.** Both implausible dates were accepted and stored. After the fix: *"is in the future"* and *"is before 1900 — check the year"*; the 2027 next-service date still accepted. | **FAIL → PASS after fix** | Bug 3 in `DEBUGGING.md`. Format-only validation is not value validation |
| **8e** | Enter costs as `1,240.75`, `$500`, ` 88.50 `, `$1,000.00`; then `free of charge` | The first four stored as 1240.75 / 500.00 / 88.50 / 1000.00; the last rejected | **First run: FAILED** — `1,240.75` and `$500` were rejected outright. After the fix all four stored correctly and `free of charge` still rejected. | **FAIL → PASS after fix** | Bug 4 in `DEBUGGING.md`. Our own sample data contains a $1,240.75 repair |
| **9** | **CSV import, clean file:** 2 valid equipment rows | Both inserted with correct values | Count rose by 2; `year = 2024` stored correctly. | **PASS** | — |
| **9b** | **CSV import, dirty file:** 8 rows containing a blank name, a blank manufacturer, an invalid type, a non-numeric year, a duplicate serial, a bad date and an invalid status | Exactly 1 row inserted; the other 7 listed with specific reasons | Count rose by exactly 1. Response contained all seven expected reasons. | **PASS** | Partial commit is deliberate — README limitation 6 |
| **9c** | CSV containing the **same serial number twice within the file** | Only the first inserted; the second rejected | Count rose by 1; message *"appears twice in this file"*. | **PASS** | The database check cannot catch this — neither row is inserted yet when the second is validated |
| **9d** | CSV whose header is `wrong,header` | Rejected before any row is read | *"CSV is missing required column(s): …"*; count unchanged. | **PASS** | — |
| **9e** | CSV as Excel actually writes it: UTF-8 byte-order mark, CRLF line endings, every field padded with spaces | Imported cleanly with whitespace stripped | Row inserted; `name` stored as `"TEST 9e Claas Arion"` (padding removed), `equipment_type` as `"Tractor"`. | **PASS** | `utf-8-sig` decoding is what makes the BOM disappear |
| **10** | `GET` each of the 16 pages: dashboard, equipment, add/detail/edit, repairs, add/edit, maintenance, add/edit, mechanics, reports, import, schema, about | All return HTTP 200 and contain "FarmFix" | All 16 returned 200 with the string present. | **PASS** (16 cases) | — |
| **10b** | `GET /equipment/99999`, `/repairs/99999/edit`, `/no-such-page` | The first two redirect with a message rather than crashing; the last returns 404 | Redirects returned 200 after following; `/no-such-page` returned 404. | **PASS** | — |
| **10c** | Compare the dashboard's printed totals against the database | `$4,381.20`, `$2,014.75` and `$6,395.95` all appear on the page | All three present; row counts confirmed at 10 and 11. | **PASS** | Catches a dashboard that renders but reads the wrong table |
| **11** | Read the schema back from SQLite's own metadata | All four tables present; `repairs` has exactly two FKs with the declared delete actions; `maintenance` has one; every table has a PK; `equipment_id` is NOT NULL and `mechanic_id` is not; page reports no integrity problems | Tables `{equipment, repairs, maintenance, mechanics}` found. `repairs` FK set was exactly `{(equipment_id, equipment, CASCADE), (mechanic_id, mechanics, SET NULL)}`. `maintenance`: `{(equipment_id, equipment, CASCADE)}`. All four had a PK column. `notnull` was 1 for `equipment_id`, 0 for `mechanic_id`. Page contained *"PRAGMA foreign_key_check returned no rows"*. | **PASS** | Pins the schema so a future edit cannot silently change a delete rule |

**65 automated cases. 65 passing. Four of them (8c, 8d, 8e, and the first
attempt at 8e's assertion) failed on their first run and were fixed.**

---

## Manual and exploratory tests

Run by hand against the real `database/farmfix.db` and in a real browser. Four
of these found the problems above.

| # | Action | Expected | Actual | Pass/Fail | Notes |
|---|---|---|---|---|---|
| **M-1** | Run the app against a database where all four tables are **empty** | Every page renders; no crash on `SUM` over zero rows, no division by zero | All 12 pages returned HTTP 200. Aggregates rendered as `$0.00` thanks to `COALESCE` and the `money` filter's `None` handling. | **PASS** | `SUM()` over no rows returns `NULL`, not 0 — worth checking deliberately |
| **M-2** | Register a machine and open its detail page before adding any history | Renders with zeroes, no "not scheduled" confusion | 200. Repairs 0, Services 0, lifetime $0.00, "Nothing scheduled". Reports page also fine. | **PASS** | — |
| **M-3** | Type `%`, `_`, `%%` into the equipment search box | Nothing matches | **All 5 machines matched.** | **FAIL → fixed** | Bug 1 |
| **M-4** | Enter a repair dated `2099-01-01` and `1899-01-01` | Rejected | **Both accepted and stored.** | **FAIL → fixed** | Bug 3 |
| **M-5** | Type `$1,240.75` in the cost field — the exact figure from our own sample data | Accepted | **Rejected:** *"cost '1,240.75' is not a number"*. | **FAIL → fixed** | Bug 4 |
| **M-6** | Compute the lifetime-cost report two ways and compare | Identical | **Not identical** — the two-join version was 2–3× too high. | **FAIL → fixed** | Bug 2 |
| **M-7** | Try `' OR 1=1 --` in the search box | No rows, no error | 0 rows, HTTP 200. | **PASS** | Bound parameters working as intended |
| **M-8** | Edit a machine, keeping its own serial number unchanged; then try to take another machine's serial | First succeeds; second is rejected | First: *"Updated 'John Deere 5075E'"*, status changed. Second: *"serial number 'KBTL3902P2201887' is already registered"*. | **PASS** | The uniqueness check has to exclude the row being edited |
| **M-9** | Reassign a repair to a different machine via the edit form | Foreign key updates; the repair moves between history pages | `equipment_id` changed from 2 to 3; it disappeared from one detail page and appeared on the other. | **PASS** | — |
| **M-10** | Leave the cost field blank on a repair | Stored as `0.0`, not `NULL` or an error | Stored as `0.0`. | **PASS** | Warranty repairs genuinely cost nothing |
| **M-11** | Odd filter values: reversed date range, `min_cost=-500`, `min_cost=1e400`, `equipment_id=abc`, `mechanic_id=abc` | No crash | All returned HTTP 200 with an empty or unfiltered result. | **PASS** | — |
| **M-12** | 300-character equipment name; 5,000-character repair notes | Name rejected; notes accepted | Name: *"must be 100 characters or fewer"*. Notes: accepted (`TEXT` is unbounded, which is correct). | **PASS** | — |
| **M-13** | View all pages at 1440×1000, 834×1112 and 390×844; check for horizontal page scroll and JavaScript console errors | No page scrolls sideways; no console errors | 11 pages × 3 widths checked. **Zero** horizontal-overflow cases, **zero** console errors. Wide tables scroll inside their own container; the nav collapses to a Menu button below 900 px. | **PASS** | Automated with a headless browser |
| **M-14** | Rebuild the database and walk the full demo scenario, checking every figure | Numbers return to the starting state after the delete | Start $6,395.95 → add machine → +repair $385 → +service $155 → edit repair to $410 → lifetime $565.00 → delete → back to **$6,395.95** exactly, `foreign_key_check` clean. | **PASS** | Every figure in `DEMO_SCRIPT.md` came from this run |

---

## Coverage against the assignment's SQL requirements

| Requirement | Where it is exercised |
|---|---|
| `CREATE TABLE` | `database/schema.sql`; test 11 reads the definitions back |
| `INSERT` | Tests 1, 2, 4, 9; add forms for all four tables; CSV import |
| `SELECT` | Tests 3, 8, 10; every page |
| `UPDATE` | Tests 5, 5b; M-8, M-9 |
| `DELETE` | Tests 6, 6b, 6c, 6d |
| `WHERE` | Tests 8, 8b, 8c; every filter and every `… WHERE id = ?` |
| `ORDER BY` | Test 8; every sortable column heading; every report |
| `GROUP BY` | Tests 3, 3b; Reports page (6 grouped panels), Mechanics page |
| `HAVING` | Reports → "Problem machines" (`COUNT(*) >= 2 AND SUM(cost) > 500`) |
| Aggregate functions | Tests 3, 10c; `COUNT`, `SUM`, `AVG`, `MIN`, `MAX` all on screen with labels |
| `JOIN` (INNER and LEFT) | Tests 2, 3, 6c, 8; equipment detail, repairs list, every report |
| `UNION ALL` | Dashboard "Recent activity" |
| Primary keys | Test 11 |
| Foreign keys + enforcement | Tests 2, 6b, 6c, 7, 7b, 11 |
| Constraints (`CHECK`, `UNIQUE`, `NOT NULL`) | Tests 1b, 2c, 4c, 7c; M-8 |
| Schema inspection | Test 11; the Schema page; `init_db.py` output |
| CSV import + validation | Tests 9, 9b, 9c, 9d, 9e |
| Connecting SQLite3 to the backend | Every test — they all go through `app.get_db()` |
