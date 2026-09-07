-- ============================================================
-- FarmFix — Farm Equipment Repair & Maintenance Tracker
-- COMP 368 Database Systems, Project 1
-- Team: Ayush Gaire, Ashish Gaire, AJ Rayamajhi
--
-- SQLite3 schema, derived directly from the UML class diagram in
-- uml/uml-source.md.  See documentation/UML_MAPPING.md for the
-- class-by-class reasoning behind every key and constraint.
-- ============================================================

-- SQLite does NOT enforce foreign keys unless asked to, and the setting
-- lives on the CONNECTION, not in the file.  app.py issues this in
-- get_db() on every request; init_db.py issues it here.
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS maintenance;
DROP TABLE IF EXISTS repairs;
DROP TABLE IF EXISTS mechanics;
DROP TABLE IF EXISTS equipment;

-- ------------------------------------------------------------
-- UML class Equipment  ->  table equipment
--
-- Identifier equipment_id -> INTEGER PRIMARY KEY.  In SQLite this is an
-- alias for the internal rowid, so it auto-increments without needing
-- the AUTOINCREMENT keyword (which only adds bookkeeping overhead).
-- ------------------------------------------------------------
CREATE TABLE equipment (
    equipment_id   INTEGER PRIMARY KEY,
    name           TEXT    NOT NULL,
    equipment_type TEXT    NOT NULL DEFAULT 'Tractor'
                   CHECK (equipment_type IN
                          ('Tractor','Combine','Planter','Sprayer','Baler',
                           'Tillage','Loader','Truck','Irrigation','Other')),
    manufacturer   TEXT    NOT NULL,
    model          TEXT,
    year           INTEGER CHECK (year BETWEEN 1900 AND 2100),
    serial_number  TEXT    UNIQUE,          -- the machine's natural key
    purchase_date  TEXT,                    -- ISO 'YYYY-MM-DD'
    status         TEXT    NOT NULL DEFAULT 'Operational'
                   CHECK (status IN
                          ('Operational','Needs Repair','In Repair',
                           'Out of Service','Retired'))
);

-- ------------------------------------------------------------
-- UML class Mechanic  ->  table mechanics
--
-- A small lookup table.  Without it, repairs.mechanic_name would be free
-- text, and "Dale Hutchins", "Dale H." and "dale hutchins" would count as
-- three different people -- which breaks the "spending per mechanic"
-- report.  Storing the name once and referencing it by id is the
-- third-normal-form fix.
-- ------------------------------------------------------------
CREATE TABLE mechanics (
    mechanic_id INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    shop        TEXT,
    phone       TEXT,
    specialty   TEXT
);

-- ------------------------------------------------------------
-- UML class Repair  ->  table repairs
--
-- Equipment (1) ---- (0..*) Repair
--   equipment_id is NOT NULL: multiplicity 1 on the parent side means a
--   repair cannot exist without the machine it was performed on.
--   ON DELETE CASCADE: scrapping a machine removes its repair history,
--   because that history has no meaning without the machine.
--
-- Mechanic (0..1) ---- (0..*) Repair
--   mechanic_id is NULLABLE: multiplicity 0..1, because a farmer very
--   often does the repair themselves and there is no mechanic to record.
--   ON DELETE SET NULL: removing a mechanic from the contact list must
--   not delete the repair records they worked on -- the repair still
--   happened and still cost money.
-- ------------------------------------------------------------
CREATE TABLE repairs (
    repair_id          INTEGER PRIMARY KEY,
    equipment_id       INTEGER NOT NULL,
    mechanic_id        INTEGER,                       -- NULL = done in-house
    repair_date        TEXT    NOT NULL,              -- ISO 'YYYY-MM-DD'
    problem            TEXT    NOT NULL,
    repair_description TEXT,
    cost               REAL    NOT NULL DEFAULT 0 CHECK (cost >= 0),
    notes              TEXT,
    FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id) ON DELETE CASCADE,
    FOREIGN KEY (mechanic_id)  REFERENCES mechanics(mechanic_id)  ON DELETE SET NULL
);

-- ------------------------------------------------------------
-- UML class Maintenance  ->  table maintenance
--
-- Equipment (1) ---- (0..*) Maintenance, same reasoning as repairs.
--
-- next_service_date is nullable: some services (a one-off inspection)
-- do not schedule a follow-up.  A NULL here is genuinely "not scheduled",
-- which is why the Dashboard's upcoming-service query filters it out
-- rather than treating it as a date.
-- ------------------------------------------------------------
CREATE TABLE maintenance (
    maintenance_id    INTEGER PRIMARY KEY,
    equipment_id      INTEGER NOT NULL,
    service_date      TEXT    NOT NULL,               -- ISO 'YYYY-MM-DD'
    service_type      TEXT    NOT NULL
                      CHECK (service_type IN
                             ('Oil Change','Filter Replacement','Tire Inspection',
                              'Engine Service','Hydraulic Service','Grease / Lubrication',
                              'Coolant Service','Belt / Chain Service','General Inspection',
                              'Other')),
    description       TEXT,
    cost              REAL    NOT NULL DEFAULT 0 CHECK (cost >= 0),
    next_service_date TEXT,                           -- NULL = none scheduled
    notes             TEXT,
    FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- Indexes.  SQLite indexes the PRIMARY KEY and every UNIQUE column
-- automatically, but NOT the child side of a foreign key -- and every
-- JOIN in this application is on exactly those columns.
-- ------------------------------------------------------------
CREATE INDEX idx_repairs_equipment     ON repairs(equipment_id);
CREATE INDEX idx_repairs_mechanic      ON repairs(mechanic_id);
CREATE INDEX idx_repairs_date          ON repairs(repair_date);
CREATE INDEX idx_maintenance_equipment ON maintenance(equipment_id);
CREATE INDEX idx_maintenance_next      ON maintenance(next_service_date);
