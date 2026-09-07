# Zoom Demo Script (3–5 minutes)

**FarmFix · COMP 368 Database Systems, Project 1**
Ayush Gaire · Ashish Gaire · AJ Rayamajhi

**Target length: 4 minutes 30 seconds.** Hard ceiling 5:00.
Rule for the whole recording: **show the application working.** Do not read
source code aloud. The only code on screen is what the "Show SQL" buttons
reveal, and you talk over it rather than reading it line by line.

---

## Before you hit record

- [ ] Rebuild the database so every number below is exactly right:
      `python database/init_db.py`
- [ ] Start the app: `python app.py`
- [ ] Open <http://127.0.0.1:5000> and confirm the dashboard reads
      **5 equipment · 10 repairs · 11 services · $4,381.20 · $2,014.75 ·
      $6,395.95 · 1 service past due**
- [ ] Open `uml/uml-diagram.png` in a second window or tab
- [ ] Browser zoom ~110 %, other tabs closed, bookmarks bar hidden
- [ ] All three presenters on the call; one screen shared

---

## Running order and speaking parts

| Time | Section | Speaker | On screen |
|---|---|---|---|
| 0:00 – 0:35 | Problem and idea | **Ayush** | Dashboard |
| 0:35 – 1:15 | UML class diagram | **Ashish** | `uml-diagram.png` |
| 1:15 – 1:50 | The SQLite3 database | **AJ** | Schema page |
| 1:50 – 3:25 | End-to-end scenario | **Ayush** drives; **AJ** narrates the totals | Dashboard → Equipment → Add → Detail → Repair → Service → Edit → Reports → Delete |
| 3:25 – 4:00 | Reports: JOIN, GROUP BY, HAVING | **Ashish** | Reports page |
| 4:00 – 4:30 | What we learned | all three, ~10 s each | About Project page |

---

## 0:00 – 0:35 · Problem and idea — **Ayush**

> "This is FarmFix, our COMP 368 project. Team: me, Ashish Gaire, and AJ
> Rayamajhi.
>
> The problem is one every farm has. Repair and service history lives in
> memory, in a notebook in the shop, and in receipts in the glovebox. So records
> get lost, repairs get done twice, and nobody can answer the question that
> actually matters at the end of a season: which machine is costing us the most
> to keep running?
>
> FarmFix puts equipment, repairs and service records in one relational SQLite3
> database. Everything on this dashboard — five machines, ten repairs, eleven
> service records, $4,381 in repairs, $2,014 in maintenance, and one service
> that is past due — is calculated by SQL against a real database file at the
> moment the page loads. Nothing is stored in the browser."

*Scroll slowly down the dashboard while talking. Do not click yet.*

---

## 0:35 – 1:15 · UML class diagram — **Ashish**

*Switch to `uml/uml-diagram.png`.*

> "We designed the database as a UML class diagram before writing any SQL. Four
> classes.
>
> **Equipment** is the centre, with `equipment_id` as its identifier.
>
> **Repair** and **Maintenance** hang off it. Read the multiplicities: one piece
> of Equipment *has* zero-to-many Repairs, and *receives* zero-to-many
> Maintenance records. Both are one-to-many, so the foreign key goes on the
> many side — `equipment_id` on each child table. No junction table, because a
> junction table is the right answer to a many-to-many and the wrong answer to
> a one-to-many. Adding one here would let a single repair belong to two
> tractors.
>
> **Mechanic** is the interesting one. Look at the multiplicity: zero-to-one, not
> one. A farmer does a lot of repairs himself — there is no mechanic and no
> invoice. So `mechanic_id` is nullable, and that one decision drives real SQL:
> every screen that shows a mechanic name has to use a LEFT JOIN, because an
> inner join would silently drop every in-house repair from the history and from
> the cost totals."

---

## 1:15 – 1:50 · The SQLite3 database — **AJ**

*Back to the app. Click **Schema**.*

> "Here is the database inspecting itself. None of this page is hard-coded —
> it's read live from `sqlite_master` and SQLite's PRAGMA commands.
>
> Four tables, each with a primary key. Look at the delete rules, because they
> are all different and each one answers the same question: what does this record
> mean if its parent disappears? `repairs.equipment_id` is CASCADE — scrap the
> machine and its history has no subject. `repairs.mechanic_id` is SET NULL —
> take a mechanic out of the contact list and the repair *still happened and
> still cost money*, so the record survives with no mechanic attached.
>
> One thing that caught us out early: SQLite ships with foreign key enforcement
> switched **off**. Declaring FOREIGN KEY does nothing until you run
> `PRAGMA foreign_keys = ON`, and it's per connection, not stored in the file.
> This tile shows it's ON right now, and this green bar is
> `PRAGMA foreign_key_check` confirming there are no orphaned rows."

*Point at the "Foreign keys: ON" tile, the green integrity bar, and the
CASCADE / SET NULL badges on the `repairs` table. Then move on.*

---

## 1:50 – 3:25 · End-to-end scenario — **Ayush** driving, **AJ** on the totals

**This is the most important 95 seconds of the video.** Every number below was
checked against the shipped database — if one does not match, the data has been
changed; rebuild it.

| Step | Action | Say / point out | Expected on screen |
|---|---|---|---|
| **1** | **Dashboard** | "Starting point: 5 machines, 10 repairs, 11 services, $6,395.95 combined." | `5 · 10 · 11` · `$4,381.20` · `$2,014.75` · `$6,395.95` |
| **2** | Click **Equipment** | "Here's the fleet. Search runs one WHERE clause across name, make, model and serial." | 5 machines listed |
| **3** | Click **+ Add equipment** | "We just bought a tractor." | The form |
| **4** | Fill in: **Massey Ferguson 4707** · Tractor · **Massey Ferguson** · **4707** · **2022** · serial **MF4707J2204410** · purchased **2022-03-08** · Operational. Click **Save to database** | "One parameterised INSERT. The serial number is UNIQUE, so we can't register the same machine twice." | Green flash *Registered "Massey Ferguson 4707"*, and it opens the new machine's page |
| **5** | *(you are already on the detail page)* | "Brand new, so no history: zero repairs, zero services, $0.00 lifetime." | Repairs **0**, Services **0**, Lifetime **$0.00** |
| **6** | Click **+ Log repair**. Machine is pre-filled. Mechanic **Marcy Olsen**, date **2026-09-02**, problem **Hydraulic remote leaking at the coupler**, what was done **Replaced coupler seal kit and O-rings**, cost **385.00**. Save | "The machine dropdown is the foreign key. SQLite refuses the row if that machine doesn't exist." | Green flash; back on the detail page |
| **7** | Click **+ Log service**. Type **Oil Change**, date **2026-09-03**, description **First service after purchase**, cost **155.00**, next due **2027-03-03**. Save | "Different table, same foreign key." | Green flash |
| **8** | *(on the detail page)* | *(AJ)* "And there's the join. Repair history, service history, and the cost totals — three tables tied together by `equipment_id`. Lifetime cost $540." | Repairs **1** · $385.00 · Services **1** · $155.00 · **Lifetime $540.00** · Next scheduled **Mar 3, 2027** |
| **9** | Click **Show SQL** on Repair history | "LEFT JOIN to mechanics, for the reason Ashish gave." *(2 seconds — don't read it)* | SQL panel opens |
| **10** | Click **Edit** on the repair, change cost to **410.00**, Update | "That's an UPDATE, not a new row." | Green flash; still **1** repair |
| **11** | *(detail page)* | *(AJ)* "Lifetime cost recalculated to $565. Nothing was updated by hand — the query just ran again." | Repairs **$410.00** · **Lifetime $565.00** |
| **12** | Click **Reports** | *(AJ)* "Lifetime cost by machine, worst first. The new tractor is bottom at $565; the Case IH combine is top at $2,851." | Case IH **$2,851.00** … Massey Ferguson **$565.00** |
| **13** | Scroll to **Repair spending by mechanic**, click **Show SQL** | "LEFT JOIN plus COALESCE, so the in-house repairs — the ones with a NULL mechanic — get grouped and reported instead of vanishing." | Dale Hutchins · Marcy Olsen · Travis Boyd · **In-house (no mechanic)** |
| **14** | Back to the new machine, scroll down, **Delete equipment and its history**, confirm | "One DELETE. Both foreign keys are ON DELETE CASCADE, so SQLite removes the repair and the service record itself." | Flash: *Deleted … along with 1 repair(s) and 1 service record(s) (ON DELETE CASCADE)* |
| **15** | Click **Dashboard** | "Exactly back where we started. The database is the only source of truth." | `5 · 10 · 11` · **$6,395.95** |

*If you are running short on time, step 13 is the first thing to cut.*

---

## 3:25 – 4:00 · Reports — **Ashish**

*Click **Reports**. Scroll; don't open everything.*

> "Eight read-only queries that the raw lists can't answer.
>
> Repair cost by machine is a LEFT JOIN and a GROUP BY, with COUNT, SUM, AVG,
> MIN and MAX in one statement. We use LEFT JOIN deliberately — an inner join
> drops a machine with no repairs, and on a *cost* report 'missing' reads as 'we
> don't track it' rather than 'it hasn't cost us anything'.
>
> Repairs by month uses `strftime`, because SQLite has no date type — dates are
> ISO text and we extract the month to group on.
>
> And this one uses HAVING rather than WHERE. WHERE filters rows *before*
> grouping; HAVING filters the groups *after*. This is every machine with at
> least two repairs **and** more than $500 of repair spending — the Case IH at
> $2,021 and the 5075E at $994. That's the list you take into the winter."

*Click **Show SQL** on the Problem machines panel for two seconds.*

---

## 4:00 – 4:30 · What we learned — all three

About ten seconds each. Say your own version; these are the beats.

**Ayush:**
> "Declaring a foreign key in SQLite isn't the same as enforcing one. We wrote a
> test that inserts an orphan row *without* the PRAGMA, to prove the constraint
> only works because we turn it on."

**Ashish:**
> "That a JOIN changes how many rows you have, and every SUM after it is
> computed over that changed set. Our first cost report joined both child tables
> at once and tripled every total — valid SQL, no error, wrong answer."

**AJ:**
> "How much we had to check the AI. It gave us a search box that looked fine and
> was parameterised — but typing a percent sign returned every machine on the
> farm, because LIKE read it as a wildcard. We only found it by trying to break
> our own app. It's in our debugging write-up."

*End on the **About Project** page.*

> *(Ayush)* "Thanks — the full write-up, UML source, 65 tests and the database
> file are all in the submitted folder."

**Stop recording.**

---

## Timing safety net

If you are over 5:00 in rehearsal, cut in this order:

1. Step 13, mechanic spending *(saves ~20 s)*
2. Step 9, the Show SQL click on repair history *(saves ~10 s)*
3. The Show SQL click in the Reports section *(saves ~10 s)*
4. Trim the Schema section to the FK tile and the CASCADE/SET NULL badges only
   *(saves ~15 s)*

**Never cut:** the UML explanation of the `0..1` mechanic multiplicity, or steps
4–8 and 11–15 of the scenario. Those are what the assignment is grading.

---

## Recovery notes

- **A number doesn't match this script.** Someone has changed the data. Say "one
  moment", run `python database/init_db.py`, refresh, and carry on. Better:
  rebuild immediately before recording.
- **Delete asks for confirmation.** That's the browser's own dialog. Click OK.
- **The app won't start.** Run `python database/init_db.py` first — `app.py`
  refuses to run without `database/farmfix.db` and prints exactly that message.
- **A form rejects something you typed.** Read the red message aloud — it is a
  feature, not a stumble. "That's the CHECK constraint doing its job" is a good
  save.
