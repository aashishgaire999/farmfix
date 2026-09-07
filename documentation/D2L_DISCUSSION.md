# D2L Discussion Post — ready to paste

**Instructions:** copy everything between the two rules below into the D2L
discussion. Before posting, fill in the video link and the six placeholders —
those are the only things left blank on purpose.

---
---

**Project Title:** FarmFix — Farm Equipment Repair & Maintenance Tracker

**Video Demo Link:** [PASTE ZOOM LINK]

**Team Members:**
- Ayush Gaire
- Ashish Gaire
- AJ Rayamajhi

---

**Individual Contributions:**

- **Ayush Gaire:** [ENTER ACTUAL CONTRIBUTION]
- **Ashish Gaire:** [ENTER ACTUAL CONTRIBUTION]
- **AJ Rayamajhi:** [ENTER ACTUAL CONTRIBUTION]

---

**Project Summary:**

FarmFix is a Flask web application backed by a real SQLite3 database file that
gives a farm one organised place to keep equipment repair and service history.

The problem is one every farm has. Repair records live in someone's memory, in a
notebook in the shop, and in receipts in the glovebox. So history gets lost,
repairs get done twice, service intervals get missed, and nobody can answer the
question that actually matters at the end of a season: which machine is costing
the most to keep running? That last question is what makes this a database
problem rather than a spreadsheet problem — answering it means totalling two
different kinds of record, grouped by machine, and the answer has to be
recomputed every time a new repair is entered, not stored and left to go stale.

The database has four tables, derived directly from our UML class diagram.
`equipment` is the centre. `repairs` and `maintenance` each carry a NOT NULL
foreign key `equipment_id`, implementing the two one-to-many associations
(Equipment 1 → 0..* Repair, and Equipment 1 → 0..* Maintenance) — the foreign key
goes on the "many" side, and no junction table is needed, because a junction
table is the right answer to a many-to-many and the wrong answer to a
one-to-many. The fourth table, `mechanics`, is a small lookup table: without it
the mechanic's name would be free text on every repair, and "Dale Hutchins",
"Dale H." and "dale hutchins" would count as three different people, which breaks
the spending-per-mechanic report entirely.

The most interesting design decision was that `repairs.mechanic_id` is
**nullable** — multiplicity 0..1, not 1 — because farmers do a lot of repairs
themselves and there is genuinely no mechanic to record. That one choice drives
real SQL: every screen showing a repair with its mechanic has to use a LEFT JOIN,
because an inner join would silently drop all the in-house repairs from the
history and from the cost totals. The three foreign keys also have three
different ON DELETE behaviours, each answering the same question — what does this
record mean if its parent disappears? Deleting a machine CASCADEs to its history,
because a repair with no machine is meaningless. Deleting a mechanic SETs NULL,
because the repair still happened and still cost $615.40; that money left the
farm whether or not the mechanic is still in our contact list.

The application demonstrates full CRUD on equipment, repairs and maintenance —
every button runs real SQL, nothing is faked in the browser — plus WHERE
filtering, ORDER BY sorting, GROUP BY, HAVING, all five aggregate functions,
INNER and LEFT JOINs, UNION ALL, and correlated subqueries. There is an equipment
detail page that pulls one machine's complete repair and service history from
three tables joined on `equipment_id`, eight cost and scheduling reports, a CSV
importer that validates every row against the same rules as the web forms, and a
schema page that inspects the database live through `sqlite_master` and SQLite's
PRAGMA commands. Every page with a query has a "Show SQL" button that reveals the
exact statement behind what is on screen.

Stack: Python 3 + Flask, Jinja2 templates, hand-written CSS, vanilla JavaScript,
and Python's standard-library `sqlite3` module. No ORM — every query is SQL we
wrote and can explain. One runtime dependency. 65 automated tests, all passing.

---

**AI-Assisted Learning and Development Reflection:**

We used an AI assistant to learn SQLite3, and the most valuable thing it did was
explain the SQLite-specific rules that are easy to get wrong: that
`INTEGER PRIMARY KEY` auto-increments without the AUTOINCREMENT keyword, that
SQLite has no DATE type so dates are ISO text handled with `strftime()`, and that
declared column types are affinities rather than strict rules — which is why
application-side validation is load-bearing here in a way it would not be on
PostgreSQL.

The single most important thing we learned is that **declaring a foreign key in
SQLite does not enforce it.** Enforcement is off by default and must be turned on
with `PRAGMA foreign_keys = ON` on *every* connection, because the setting lives
on the connection and not in the file. We did not take the AI's word for this: we
wrote two tests that run the same orphan INSERT against the same schema, one
connection with the PRAGMA and one without. The first raises IntegrityError; the
second accepts the bad row, and `PRAGMA foreign_key_check` then reports it. That
pair of tests is what actually proved it.

We also learned to be sceptical of AI output that runs without error. Two of our
four bugs came straight from AI suggestions that looked completely normal.

The first was a cost report. We asked for one query giving, per machine, the
repair count and total plus the service count and total. The AI joined both child
tables at once — the obvious approach — and it is wrong: joining two independent
child tables to the same parent produces the cross product of the children, so a
machine with 3 repairs and 3 services yields 9 rows and every cost is counted
three times. Our John Deere 5075E showed $2,982.90 in repairs when the true
figure is $994.30. The AI had even added `COUNT(DISTINCT ...)`, which reads as
careful defensive SQL — and that addition is exactly what hid the error, because
it kept the counts correct beside sums that were 200–300% too high. We found it
only by reconciling the report against `SELECT SUM(cost) FROM repairs` and
noticing it did not balance. The fix was a correlated subquery per total, so each
table is aggregated independently and nothing multiplies.

The second was our search box. The AI wrote it with the search term bound as a
`?` parameter and correctly noted that this is not vulnerable to SQL injection.
That was true and too narrow. A bound parameter protects the SQL *statement*; it
does not stop the value being read as a *LIKE pattern*. Typing a single percent
sign into the search box returned every machine on the farm, because LIKE reads
`%` as "any sequence of characters" — and `_` behaves the same way. This is not
hypothetical: machinery model codes and serial numbers genuinely contain
underscores, so searching for model `X_200` would have returned the whole fleet.
The fix was to escape the wildcards in the term and add `ESCAPE '\'` to the LIKE
clauses. We found this by deliberately typing awkward characters into our own
search box, not by using the app normally.

Two further bugs came from our own code rather than the AI's: dates were
validated for format but not plausibility, so a repair dated 2099-01-01 was
accepted; and costs were parsed with plain `float()`, so `$1,240.75` copied
straight off an invoice was rejected — a figure that appears in our own sample
data.

What we took away: **verification is the actual work.** Generating a query took
seconds; establishing that it returned the right rows took most of an evening and
produced all the real learning. The AI was equally confident when right and when
wrong, so confidence carried no information — the only defence was checking every
result against something independent: a hand-computed total, a second
implementation in Python, or a test written specifically to fail against the
wrong answer. Not one of our four bugs produced an error message. Every one was
valid SQL or valid Python that ran cleanly and gave the wrong answer, and three
of the four were found by deliberately trying to break our own application rather
than by using it correctly.

Full documentation of six AI interactions, including both mistakes, is in
`documentation/AI_LEARNING_EVIDENCE.md`; the four debugging write-ups are in
`documentation/DEBUGGING.md`. Our test suite is 65 cases; all 65 pass.

---

**Individual Reflection:**

**Ayush:** [Write one important thing you learned.]

**Ashish:** [Write one important thing you learned.]

**AJ:** [Write one important thing you learned.]

---
---

*End of post.*
