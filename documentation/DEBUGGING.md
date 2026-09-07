# Debugging Documentation

**FarmFix · COMP 368 Database Systems, Project 1**
Ayush Gaire · Ashish Gaire · AJ Rayamajhi

Four defects found during development. All four are real, all four were found by
testing rather than by reading, and all four are fixed with a regression test
that fails against the old code. Every number quoted below was produced by
actually running the query.

The pattern across all of them: **none produced an error message.** Every one
was valid SQL or valid Python that ran cleanly and gave the wrong answer.

---

## Bug 1 — Searching for a literal `%` returned every machine

### Problem

The equipment page has one search box that looks across name, manufacturer,
model and serial number. Typing `%` into it returned **all 5 machines**. Typing
`_` also returned all 5.

### Error message / unexpected behaviour

None. No exception, nothing in the Flask log, HTTP 200. The page rendered
perfectly and reported "5 machines" — it just reported the wrong 5.

### Likely cause

`%` and `_` are the wildcard characters in SQL `LIKE`. Our search built the
pattern like this:

```python
where.append("(e.name LIKE ? OR e.manufacturer LIKE ? OR ...)")
params.extend([f"%{search}%"] * 4)
```

With `search = "%"` the pattern becomes `'%%%'`, which is "anything, anything,
anything" — it matches every row. With `search = "_"` the pattern is `'%_%'`,
which means "any string containing at least one character" — also every row.

The user's input was being interpreted as *pattern syntax* rather than as *text
to look for*. This is the same class of mistake as SQL injection, except that
here the bound parameter is doing its job correctly: `?` protects the SQL
**statement**, but it does not stop the value from being read as a LIKE pattern
once it arrives.

### Investigation

We found it by deliberately probing the search box with awkward input rather
than by using it normally:

```
   equipment search '%'        -> 5 matched
   equipment search '_'        -> 5 matched
   equipment search '%%'       -> 5 matched
   equipment search '5075'     -> 1 matched      (correct)
```

We then checked whether this was hypothetical or real, and it is real: machinery
model codes and serial numbers genuinely contain underscores. A user searching
for model `X_200` would get back **every machine on the farm**, and would
reasonably conclude the search box is broken.

We also checked that the SQL statement itself was safe — `' OR 1=1 --` returned
0 matches, confirming the bound parameter was doing its job. So the problem was
specific to the pattern, not to injection.

### Solution

Escape the wildcard characters in the user's term, and tell `LIKE` which
character is the escape:

```python
def like_term(text):
    """Wrap a search term for LIKE, escaping the wildcards % and _."""
    escaped = (
        str(text).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    )
    return f"%{escaped}%"
```

```sql
(e.name LIKE ? ESCAPE '\' OR e.manufacturer LIKE ? ESCAPE '\'
 OR e.model LIKE ? ESCAPE '\' OR e.serial_number LIKE ? ESCAPE '\')
```

The backslash itself has to be escaped **first**, otherwise the backslashes
added for `%` and `_` would themselves be doubled by the later replacement.

The same fix was applied to the repairs page, which searches `problem` and
`repair_description`.

### Retest

```
   equipment search '%'        -> 0 matched
   equipment search '_'        -> 0 matched
   equipment search '%%'       -> 0 matched
   equipment search '5075'     -> 1 matched
   equipment search '1LV5075'  -> 1 matched
   equipment search 'Deere'    -> 2 matched
   repairs   search '%'        -> 0 matched
```

Regression test `test_08c_search_treats_percent_and_underscore_literally`
asserts that each wildcard returns zero matches, then inserts a machine whose
model genuinely contains an underscore (`X_200`) and asserts that searching for
it returns **exactly one** row rather than all of them. It fails against the old
code.

### Final result

**Fixed.** Ordinary searches are unchanged; literal wildcards are now searched
for literally.

---

## Bug 2 — Two LEFT JOINs tripled every cost total

### Problem

The Reports page needs one row per machine showing total repair cost, total
service cost, and the two added together. Repairs and services are in two
different tables, so the obvious query joins both.

The obvious query is wrong.

### Error message / unexpected behaviour

Again none — valid SQL, HTTP 200, and numbers that looked plausible until we
added them up.

### Likely cause

Our first hypothesis was a bad `GROUP BY`. It was not. The cause is **row
multiplication**: joining two independent child tables to the same parent
produces the *cross product* of the children. A machine with 3 repairs and 3
services yields 3 × 3 = 9 rows, so each repair cost is counted three times and
each service cost three times.

The insidious part is that `COUNT(DISTINCT ...)` still reports the right count,
so the row counts look correct next to sums that are 200–300 % too high.

### Investigation

We computed the totals twice — once with the double-join query, once one table
at a time — and compared them directly:

```
=== TRUTH: totals computed separately, one table at a time ===
  John Deere 5075E           repairs 3 = $  994.30   services 3 = $  289.50
  Kubota L3902               repairs 2 = $  483.00   services 2 = $  177.00
  Case IH Axial-Flow 6150    repairs 2 = $ 2021.00   services 2 = $  830.00
  John Deere 1775NT          repairs 1 = $  512.60   services 2 = $  445.00
  New Holland BR7060         repairs 2 = $  370.30   services 2 = $  273.25
  GRAND TOTAL                repairs $4381.20  services $2014.75

=== NAIVE: two LEFT JOINs in one query ===
  John Deere 5075E           repairs 3 = $ 2982.90   services 3 = $  868.50
  Kubota L3902               repairs 2 = $  966.00   services 2 = $  354.00
  Case IH Axial-Flow 6150    repairs 2 = $ 4042.00   services 2 = $ 1660.00
  John Deere 1775NT          repairs 1 = $ 1025.20   services 2 = $  445.00
  New Holland BR7060         repairs 2 = $  740.60   services 2 = $  546.50

=== why: rows produced by the double join ===
  John Deere 5075E           9 rows      (3 repairs x 3 services)
  Kubota L3902               4 rows      (2 x 2)
  Case IH Axial-Flow 6150    4 rows
  John Deere 1775NT          2 rows      (1 x 2)
  New Holland BR7060         4 rows
```

$994.30 became $2,982.90 — exactly three times too high, because the 5075E has
three service records. The 1775NT's single repair doubled, because it has two
services. The multiplier is different for every machine, which is why the
report still looks internally consistent and why eyeballing it does not catch
the error. Only reconciling against `SELECT SUM(cost) FROM repairs` does.

### Solution

Use a **correlated subquery per total** instead of joining both children at
once. Each subquery aggregates its own table independently, so nothing
multiplies:

```sql
SELECT e.name AS label,
       (SELECT COALESCE(SUM(r.cost),0) FROM repairs r
         WHERE r.equipment_id = e.equipment_id) AS repair_total,
       (SELECT COALESCE(SUM(m.cost),0) FROM maintenance m
         WHERE m.equipment_id = e.equipment_id) AS service_total,
       (SELECT COALESCE(SUM(r.cost),0) FROM repairs r
         WHERE r.equipment_id = e.equipment_id)
     + (SELECT COALESCE(SUM(m.cost),0) FROM maintenance m
         WHERE m.equipment_id = e.equipment_id) AS total
FROM equipment e
ORDER BY total DESC;
```

We considered two alternatives:

- **`COUNT(DISTINCT ...)` and `SUM(DISTINCT ...)`.** `SUM(DISTINCT cost)` is
  *worse*, not better: two repairs that both cost exactly $55.00 would collapse
  into one and the total would be too low. It swaps a visible over-count for an
  invisible under-count.
- **Aggregate each table in a subquery, then join the two subqueries.** This is
  correct and is what we would use on a large table. We chose correlated
  subqueries because they read top-to-bottom in one piece and all three of us
  can explain them on camera; at five machines the performance difference is
  nil.

The single-table reports (repair cost per machine, service cost per machine)
still use a plain `LEFT JOIN` + `GROUP BY`, which is correct — the problem only
arises with **two** child tables in one query.

### Retest

`test_03b_lifetime_cost_is_not_inflated_by_a_double_join` computes the truth one
table at a time, asserts the application's query matches it exactly for all five
machines, and then asserts that the naive version really does produce
`$2,982.90` for the 5075E where the truth is `$994.30`. That last assertion
exists so that nobody "simplifies" the query back to two joins later.

We also reconciled the report against the whole table: the five lifetime totals
sum to $6,395.95, which equals `SUM(repairs.cost) + SUM(maintenance.cost)`
= $4,381.20 + $2,014.75.

### Final result

**Fixed.** This is also the reason the equipment list page uses correlated
subqueries for its cost columns rather than joins.

---

## Bug 3 — A repair dated 2099 was accepted

### Problem

Validation checked the date *format* and nothing else, so `2099-01-01` and
`1899-01-01` were both stored happily as repair dates.

### Error message / unexpected behaviour

None — both are well-formed `YYYY-MM-DD` strings.

### Cause

`if not DATE_RE.match(repair_date)` tests only the shape of the string. A
mistyped year passes the regex. The consequence is not cosmetic: the repairs-by-
month report would grow a `2099-01` bucket, and the dashboard's activity feed —
which sorts by date descending — would show that phantom repair at the top
forever.

### Investigation

Found by probing the add-repair form with implausible input:

```
   1899 repair date: ['Logged repair: "time travel repair".']
   2099 repair date: ['Logged repair: "future repair".']
```

### Solution

A shared `check_date()` helper that validates the format *and* the range, with
an `allow_future` flag — because there is exactly one date in the schema where
the future is correct:

```python
def check_date(value, label, errors, allow_future=False, required=True):
    ...
    if value < EARLIEST_DATE:                      # '1900-01-01'
        errors.append(f"{label} '{value}' is before 1900 — check the year")
    elif not allow_future and value > date.today().isoformat():
        errors.append(f"{label} '{value}' is in the future")
```

- `repair_date`, `service_date`, `purchase_date` — a past event, no future dates.
- `next_service_date` — `allow_future=True`, because a scheduled service *is* in
  the future.

### Retest

```
   1899 repair: ["repair date '1899-01-01' is before 1900 — check the year."]
   2099 repair: ["repair date '2099-01-01' is in the future."]
   future purchase date: ["purchase date '2030-01-01' is in the future."]
```

`test_08d_implausible_dates_are_rejected` covers both bad cases **and** asserts
that a `next_service_date` of `2027-03-03` is still accepted — otherwise the fix
would have broken the scheduling feature it was meant to leave alone.

### Final result

**Fixed.**

---

## Bug 4 — `$1,240.75` copied off an invoice was rejected

### Problem

The cost field accepted `1240.75` but rejected `1,240.75` and `$500` with
*"cost '1,240.75' is not a number"*.

### Cause

`float()` does not accept a currency symbol or a thousands separator. This is
not exotic input: our own sample data contains a repair costing $1,240.75, and
that is exactly how the figure is written on an invoice and how a spreadsheet
exports it.

### Investigation

Probing the cost field with the four ways a person actually types money:

```
   cost='1,240.75'   -> Could not save repair: cost '1,240.75' is not a number.
   cost='$500'       -> Could not save repair: cost '$500' is not a number.
   cost='500.00'     -> Logged repair.
   cost=' 500 '      -> Logged repair.
```

### Solution

A `parse_money()` helper that strips `$`, commas and spaces before parsing, and
rejects `NaN` and infinity (which `float()` will happily produce from `"nan"` or
`"1e400"`):

```python
text = str(raw or "").strip().replace("$", "").replace(",", "").replace(" ", "")
```

Because the CSV importer shares the same validation code, spreadsheet exports
with formatted currency now import correctly too.

### Retest

`test_08e_costs_copied_off_an_invoice_are_accepted` checks that `1,240.75`,
`$500`, ` 88.50 ` and `$1,000.00` are stored as `1240.75`, `500.00`, `88.50` and
`1000.00` — and that `"free of charge"` is still rejected.

**One honest note about this test:** it failed on its first run, and the failure
was in the *test*, not the application. We looked up the stored row by its
`problem` text, but the application strips whitespace from that field, so
`"TEST 8e  88.50 "` had been stored as `"TEST 8e  88.50"` and the exact-match
lookup found nothing. We fixed the lookup. It is worth recording because it is
the ordinary case: a red test is a claim that something is wrong *somewhere*,
and the first job is to find out where.

### Final result

**Fixed.**

---

## What these four have in common

1. **Not one of them raised an error.** Every one was valid SQL or valid Python
   that ran cleanly and returned a wrong answer. If we had only checked that
   pages load, we would have shipped all four.
2. **Three of the four were found by deliberately using the application
   badly** — typing `%` into a search box, typing a year with a slipped digit,
   pasting a figure straight off an invoice. Using it correctly never revealed
   any of them.
3. **The remaining one was found by adding the numbers up.** The double-join
   report looked fine until we reconciled it against
   `SELECT SUM(cost) FROM repairs`.
4. **Each fix has a test that fails against the old code.** A test that passes
   both before and after a change has verified nothing.
