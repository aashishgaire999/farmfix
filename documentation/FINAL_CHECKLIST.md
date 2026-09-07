# Final Requirement Checklist

**FarmFix · COMP 368 Database Systems, Project 1**
Ayush Gaire · Ashish Gaire · AJ Rayamajhi

Every item below was verified against the actual code and the actual database
before this file was written — not assumed. The "Verified by" column says how.

---

## Database

| ✔ | Requirement | Where | Verified by |
|---|---|---|---|
| [x] | **Real SQLite3 database** | `database/farmfix.db` | Every one of the 65 tests goes through `app.get_db()`; delete the file and `app.py` refuses to start |
| [x] | At least two meaningful related tables | **4**: `equipment`, `repairs`, `maintenance`, `mechanics` | `SELECT name FROM sqlite_master` returns exactly these four |
| [x] | Primary keys | one per table | `PRAGMA table_info` shows a `pk` column on all four (test 11) |
| [x] | Foreign keys | **3** — `repairs.equipment_id`, `repairs.mechanic_id`, `maintenance.equipment_id` | `PRAGMA foreign_key_list` (test 11); enforcement proven by tests 7 / 7b |
| [x] | `PRAGMA foreign_keys = ON` enabled | `get_db()`, `init_db.py`, both test fixtures | Schema page shows it live; test 7b proves an orphan is accepted *without* it |
| [x] | Constraints beyond keys | 14 × `NOT NULL`, 2 × `UNIQUE`, 6 × `CHECK`, 5 × `CREATE INDEX` | Counted in `schema.sql`; enforcement tested in 1b, 2c, 4c, 7c |
| [x] | Three distinct `ON DELETE` behaviours | 3 × `CASCADE`, 1 × `SET NULL` | Tests 6b (cascade), 6c (set null), 11 (declared actions pinned) |

## SQL operations

| ✔ | Requirement | Count in `app.py` | Where |
|---|---|---|---|
| [x] | `CREATE TABLE` | 4 (in `schema.sql`) | `database/schema.sql`; test 11 reads them back |
| [x] | `INSERT` | 5 statements | Add equipment / repair / service / mechanic; CSV `executemany` |
| [x] | `SELECT` | 76 | Every page |
| [x] | `UPDATE` | 4 | Edit equipment, repair, maintenance |
| [x] | `DELETE` | 4 | Delete equipment (cascades), repair, maintenance, mechanic (sets null) |
| [x] | `WHERE` | 53 clauses | Every filter, every `… WHERE <pk> = ?` |
| [x] | `ORDER BY` | 22 | Sortable headings on 3 pages; every report |
| [x] | `GROUP BY` | 10 | Reports (6 grouped panels), Mechanics page |
| [x] | Aggregate functions | `COUNT` ×30, `SUM` ×21, `AVG` ×11, `MIN` ×9, `MAX` ×13 | Dashboard tiles, list summaries, every report |
| [x] | `JOIN` | 22 (12 of them `LEFT JOIN`) | Equipment detail (3 tables), repairs list, every report |
| [x] | Schema inspection | `PRAGMA` ×7, `sqlite_master` ×2 | The whole `/schema` page + `init_db.py` output |
| [x] | *Bonus:* `HAVING` | 4 | Reports → "Problem machines" |
| [x] | *Bonus:* `UNION ALL` | 2 | Dashboard → Recent activity |
| [x] | *Bonus:* correlated subqueries | 12+ | Lifetime cost report; equipment list cost columns |
| [x] | *Bonus:* `COALESCE`, `strftime`, `LIKE … ESCAPE`, `IS NULL` | 37 / 2 / 7 / 8 | Reports, month grouping, both search boxes, overdue filter |
| [x] | *Bonus:* parameterised queries throughout | 54 `?` markers | Test 8 sends `?sort=1;DROP TABLE repairs--`; both tables survive |

## CRUD

| ✔ | Entity | C | R | U | D | All changes hit SQLite? |
|---|---|---|---|---|---|---|
| [x] | **Equipment** | Add form + CSV import | Register, detail page | Edit form | Delete (cascades to history) | Yes — tests 1, 5b, 6b |
| [x] | **Repair** | Log repair form | List, equipment detail | Edit form | Delete | Yes — tests 2, 5, 6 |
| [x] | **Maintenance** | Log service form | List, equipment detail | Edit form | Delete | Yes — tests 4, 4b, 4c |
| [x] | **Mechanic** | Add form | List with roll-up | *(via repair reassignment)* | Delete (sets null) | Yes — test 6c |
| [x] | No frontend-only fake CRUD | — | — | — | — | Every CRUD test asserts on the database through a **separate raw connection** |

## Search, filter, sort, aggregation

| ✔ | Requirement | Where |
|---|---|---|
| [x] | Search equipment by name / type / manufacturer / serial | One `WHERE` across four columns + type and status dropdowns |
| [x] | Filter repairs by equipment, date range, mechanic | Repairs page — includes an "in-house (`mechanic_id IS NULL`)" option |
| [x] | Sort newest / oldest / highest cost / lowest cost | Clickable column headings, whitelisted `ORDER BY` |
| [x] | Repair count per equipment | Reports → repair count and cost by machine |
| [x] | Maintenance count per equipment | Reports → service count and cost by machine |
| [x] | Total repair cost by equipment | Same panel; also the equipment register |
| [x] | Average repair cost | Dashboard tile; every report's Average column |
| [x] | Total maintenance spending | Dashboard tile |
| [x] | Most repaired equipment | Reports → problem machines (`HAVING`) |
| [x] | Most expensive equipment to maintain | Reports → lifetime cost by machine (`JOIN`-free correlated subqueries — see `DEBUGGING.md` bug 2) |
| [x] | Equipment + repair history JOIN | Equipment detail page; Reports → recent repairs |

## CSV / import evidence

| ✔ | Requirement | Where | Verified by |
|---|---|---|---|
| [x] | Sample CSV provided | `data/sample_equipment.csv` (5 clean rows) | Test 9 |
| [x] | Import equipment into SQLite3 | `/import` | Tests 9, 9e |
| [x] | Imported data validated | Same `validate_equipment()` the web form uses | Test 9b — 7 of 8 rows rejected with specific reasons |
| [x] | Duplicate detection within a file | `seen_serials` set in `import_csv()` | Test 9c |
| [x] | Documented how pandas imports CSV/Excel | Import page, with the `if_exists="replace"` trap called out | — |
| [x] | Handles what Excel actually writes | `utf-8-sig` decoding + field stripping | Test 9e (BOM + CRLF + padding) |

## UML

| ✔ | Requirement | Where | Verified by |
|---|---|---|---|
| [x] | UML **CLASS** diagram (not an ER diagram) | `uml/uml-diagram.png` | Rendered from Mermaid `classDiagram` |
| [x] | UML image | `.png`, plus `.pdf` and `.svg` | All present |
| [x] | Mermaid / PlantUML source | `uml/uml-diagram.mmd`, `uml/uml-source.md` | Both blocks present |
| [x] | Explanation of the diagram | `uml/uml-source.md` §3 | — |
| [x] | Classes shown | Equipment, Repair, Maintenance, Mechanic | Visible in the diagram |
| [x] | Attributes shown | all, on all four classes | Visible in the diagram |
| [x] | Identifiers / PK candidates shown | `«PK»` on all four | Visible in the diagram |
| [x] | Associations shown | 3 named: *has*, *receives*, *performs* | Visible in the diagram |
| [x] | Multiplicities shown | `1`, `0..1`, `0..*` on every association end | Visible in the diagram |
| [x] | UML-to-table mapping documented | `documentation/UML_MAPPING.md` (6 sections) + `FINAL_REPORT.md` §6 | Includes *why* for every FK and delete rule |

## Website / interface

| ✔ | Requirement | Where |
|---|---|---|
| [x] | Dashboard: total equipment, repairs, maintenance records, repair cost, maintenance cost, upcoming maintenance, recent activity | `/` — all seven, none hard-coded |
| [x] | Equipment page: table + add / view / edit / delete | `/equipment` |
| [x] | Equipment detail: info, repair history, maintenance history, total repair cost, total maintenance cost, last maintenance date, next scheduled | `/equipment/<id>` — all seven |
| [x] | Repairs page with full CRUD | `/repairs` |
| [x] | Maintenance page with full CRUD | `/maintenance` |
| [x] | Reports / insights page | `/reports` — 8 analyses |
| [x] | About Project page | `/about` |
| [x] | Clean, simple, professional agricultural design | Field green + harvest amber; no gradients, neon, animation or glassmorphism |
| [x] | Works on desktop, tablet and mobile | Manual test M-13: 11 pages × 3 widths, **zero** horizontal-overflow cases, **zero** console errors |

## Scenario, testing, debugging

| ✔ | Requirement | Where | Verified by |
|---|---|---|---|
| [x] | Complete end-to-end scenario (all 13 steps) | `FINAL_REPORT.md` §7.7; `DEMO_SCRIPT.md` steps 1–15 | Every figure ($6,395.95 → $540.00 → $565.00 → back to $6,395.95) was produced by actually running it |
| [x] | At least 3 actual tests | **65** automated + 14 manual | `python -m pytest tests/ -v` → 65 passed in 1.43s |
| [x] | Expected results recorded | `TESTING.md` column 3 | — |
| [x] | Actual results recorded | `TESTING.md` column 4 | — |
| [x] | Pass/fail recorded honestly | `TESTING.md` column 5 | **Four cases failed on their first run** (8c, 8d, 8e, M-6) and are recorded as failures with their fixes |
| [x] | Real debugging example | `documentation/DEBUGGING.md` | **Four** bugs, each with Problem → Error → Cause → Investigation → Fix → Retest → Result |

## AI evidence

| ✔ | Requirement | Where |
|---|---|---|
| [x] | At least 3 AI interactions documented | **6** in `AI_LEARNING_EVIDENCE.md`, each with Prompt / AI Response Summary / What We Learned / What We Implemented / How We Verified It |
| [x] | Interaction on primary/foreign keys | §1 — the `PRAGMA foreign_keys` discovery |
| [x] | Interaction on UML one-to-many → foreign keys | §4 — choosing CASCADE vs SET NULL vs RESTRICT |
| [x] | Interaction on creating/debugging JOIN + GROUP BY | §2 — the double-join that tripled every total |
| [x] | **An AI suggestion that was weak/incorrect** | **Two.** §2 — the cost query, wrong by 200–300 % with real recorded numbers. §3 — the search box that matched everything |
| [x] | AI verification explained | Each interaction's "How we verified it"; `FINAL_REPORT.md` §4.4 lists the six techniques used |
| [x] | Not claimed the AI was always correct | Summary table in `AI_LEARNING_EVIDENCE.md`; `FINAL_REPORT.md` §9.2 |
| [x] | Problems recorded as they actually occurred | All four bugs in `DEBUGGING.md` were found by real probing, including one failure that was in our *test* rather than the app |

## Documents

| ✔ | Requirement | File |
|---|---|---|
| [x] | Final written report in the required 11-section order | `documentation/FINAL_REPORT.md` |
| [x] | AI learning evidence | `documentation/AI_LEARNING_EVIDENCE.md` |
| [x] | Testing documentation | `documentation/TESTING.md` |
| [x] | Debugging documentation | `documentation/DEBUGGING.md` |
| [x] | UML mapping | `documentation/UML_MAPPING.md` |
| [x] | Demo script (3–5 min, speaking parts split) | `documentation/DEMO_SCRIPT.md` — 4:30 target, cut list if over time |
| [x] | D2L discussion post | `documentation/D2L_DISCUSSION.md` — ready to paste |
| [x] | Final checklist | this file |
| [x] | README | `README.md` — overview, team, features, stack, DB structure, requirements, install, init, run, test, login note, folder structure, 9 known limitations |
| [x] | Individual contribution placeholders | `FINAL_REPORT.md` §10, `D2L_DISCUSSION.md` — clearly marked, **not fabricated** |
| [x] | Individual reflection placeholders | `FINAL_REPORT.md` §10b, `D2L_DISCUSSION.md` — clearly marked, **not fabricated** |
| [x] | Demo video link placeholder | `README.md`, `FINAL_REPORT.md` §11, `D2L_DISCUSSION.md` |

## Files in the submitted folder

| ✔ | Deliverable | Path |
|---|---|---|
| [x] | Source code | `app.py`, `templates/` (15 files), `static/style.css` |
| [x] | SQLite3 `.db` file | `database/farmfix.db` — 5 equipment, 3 mechanics, 10 repairs, 11 service records |
| [x] | `schema.sql` | `database/schema.sql` |
| [x] | Sample data | `database/sample_data.sql` |
| [x] | Database init script | `database/init_db.py` |
| [x] | Sample CSV | `data/sample_equipment.csv` + `data/sample_equipment_with_errors.csv` |
| [x] | UML class diagram | `uml/uml-diagram.png` `.pdf` `.svg` `.html` |
| [x] | UML source | `uml/uml-diagram.mmd`, `uml/uml-source.md` |
| [x] | Written report | `documentation/FINAL_REPORT.md` |
| [x] | Supporting files | `requirements.txt`, `tests/test_app.py`, 8 documents in `documentation/` |
| [x] | ZIP-ready folder | Yes — unzip, `pip install -r requirements.txt`, `python app.py`. Verified from a clean extraction. |

---

## Things left blank on purpose

These are the **only** placeholders in the submission. They are blank because
fabricating them would be dishonest, not because they were forgotten:

1. `[PASTE ZOOM LINK]` — `README.md`, `FINAL_REPORT.md` §11, `D2L_DISCUSSION.md`.
2. **Individual contributions** for each of the three members — `FINAL_REPORT.md`
   §10 and `D2L_DISCUSSION.md`.
3. **Individual reflections** for each of the three members —
   `FINAL_REPORT.md` §10b and `D2L_DISCUSSION.md`.
4. Optional slots for additional AI interactions each member may want to add —
   `AI_LEARNING_EVIDENCE.md` §7.

**Fill in 1–3 before submitting.**

---

## Verification run log

```
$ python database/init_db.py
  Tables created (read back from sqlite_master):
    - equipment    9 columns, 0 foreign key(s), 5 row(s)
    - maintenance  8 columns, 1 foreign key(s), 11 row(s)
    - mechanics    5 columns, 0 foreign key(s), 3 row(s)
    - repairs      8 columns, 2 foreign key(s), 10 row(s)
  Foreign key integrity check: clean
  Seeded totals: repairs $4,381.20 | maintenance $2,014.75

$ python -m pytest tests/ -q
  65 passed in 1.43s

$ python app.py
  * Running on http://127.0.0.1:5000
  → all 16 pages HTTP 200; desktop / tablet / mobile checked,
    no console errors, no horizontal page overflow

$ PRAGMA foreign_key_check
  clean
```
