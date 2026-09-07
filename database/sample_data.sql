-- ============================================================
-- FarmFix — sample data
-- COMP 368 Database Systems, Project 1
--
-- Demonstrates the INSERT statement.  Loaded by init_db.py after
-- schema.sql.  Deliberately small (5 machines, 3 mechanics, 10 repairs,
-- 11 service records) so that every figure on screen can be checked by
-- hand during the demo.
-- All names, phone numbers, and serial numbers below are fictional demo data.
--
-- Dates run from 2026-02 to 2026-09 so the "upcoming service" query on
-- the dashboard has one overdue machine and several due soon.
-- ============================================================

PRAGMA foreign_keys = ON;

-- ---------- equipment ----------
INSERT INTO equipment
    (equipment_id, name, equipment_type, manufacturer, model, year,
     serial_number, purchase_date, status) VALUES
    (1, 'John Deere 5075E',        'Tractor', 'John Deere',  '5075E',
        2019, 'DEMO-TRACTOR-001',  '2019-04-12', 'Operational'),
    (2, 'Kubota L3902',            'Tractor', 'Kubota',      'L3902',
        2021, 'DEMO-TRACTOR-002',  '2021-05-20', 'Operational'),
    (3, 'Case IH Axial-Flow 6150', 'Combine', 'Case IH',     'Axial-Flow 6150',
        2017, 'DEMO-COMBINE-003',  '2018-08-02', 'Needs Repair'),
    (4, 'John Deere 1775NT',       'Planter', 'John Deere',  '1775NT',
        2020, 'DEMO-PLANTER-004',  '2020-03-15', 'Operational'),
    (5, 'New Holland BR7060',      'Baler',   'New Holland', 'BR7060',
        2015, 'DEMO-BALER-005',    '2016-06-10', 'Out of Service');

-- ---------- mechanics ----------
INSERT INTO mechanics (mechanic_id, name, shop, phone, specialty) VALUES
    (1, 'Demo Mechanic A', 'Demo Diesel Shop',      '555-0101', 'Diesel engines'),
    (2, 'Demo Mechanic B', 'Demo Hydraulic Shop',   '555-0102', 'Hydraulics'),
    (3, 'Demo Mechanic C', 'Demo Electrical Shop',  '555-0103', 'Electrical and sensors');

-- ---------- repairs ----------
-- mechanic_id is NULL where the work was done in-house by the operator.
INSERT INTO repairs
    (equipment_id, mechanic_id, repair_date, problem, repair_description, cost, notes) VALUES
    (1, 1,    '2026-04-02', 'Starter motor failed on cold start',
               'Replaced starter motor and cleaned battery ground strap.',
               615.40, 'Machine was down two days waiting on the part.'),
    (1, NULL, '2026-06-18', 'Alternator belt squealing under load',
               'Retensioned belt and replaced idler pulley. Done in the shop.',
               38.90,  'Parts only — no labour charge.'),
    (1, 3,    '2026-09-01', 'Cab lighting intermittent',
               'Traced chafed wiring harness behind the fender, resleeved and reloomed.',
               340.00, 'Recommend checking the other side next winter.'),
    (2, 2,    '2026-05-11', 'Front loader dropping under load',
               'Replaced leaking hydraulic hose and both fittings on the lift cylinder.',
               428.00, NULL),
    (2, NULL, '2026-07-09', 'Flat rear tire',
               'Plugged puncture and reseated bead.',
               55.00,  'Picked up a bolt in the north field.'),
    (3, 2,    '2026-07-22', 'Header height sensor reading erratically',
               'Replaced left-hand header height sensor and recalibrated.',
               780.25, NULL),
    (3, 1,    '2026-08-28', 'Rotor drive belt shredded during harvest prep',
               'Replaced rotor drive belt and both tensioner bearings.',
               1240.75,'Machine still flagged Needs Repair pending a test run.'),
    (4, 3,    '2026-05-02', 'Row unit monitor not reading seed on rows 8-12',
               'Replaced seed tube sensor harness and reseated the connector.',
               512.60, NULL),
    (5, 1,    '2026-03-14', 'Pickup tine bar bent',
               'Straightened tine bar and replaced six broken tines.',
               296.00, NULL),
    (5, NULL, '2026-08-05', 'Twine arm spring broken',
               'Fitted replacement spring from the parts bin.',
               74.30,  'Baler taken out of service until the gearbox is looked at.');

-- ---------- maintenance ----------
-- next_service_date is NULL where no follow-up was scheduled.
INSERT INTO maintenance
    (equipment_id, service_date, service_type, description, cost, next_service_date, notes) VALUES
    (1, '2026-03-20', 'Oil Change',
        'Engine oil and filter, 250-hour interval.',            145.00, '2026-09-20', NULL),
    (1, '2026-06-15', 'Filter Replacement',
        'Air, fuel and hydraulic filters.',                      89.50, '2026-12-15', NULL),
    (1, '2026-08-22', 'Tire Inspection',
        'Pressure check and tread inspection, all four.',        55.00, '2026-09-22', NULL),
    (2, '2026-04-05', 'Oil Change',
        'Engine oil and filter.',                               132.00, '2026-10-05', NULL),
    (2, '2026-08-12', 'Grease / Lubrication',
        'Full greasing of loader pins and driveline.',           45.00, '2026-09-12', 'Do this monthly in season.'),
    (3, '2026-05-30', 'Hydraulic Service',
        'Drained and refilled hydraulic system, new filters.',   620.00, '2026-11-30', NULL),
    (3, '2026-08-01', 'General Inspection',
        'Pre-harvest inspection, belts and chains checked.',     210.00, '2026-09-08', 'Recheck before harvest starts.'),
    (4, '2026-04-18', 'Tire Inspection',
        'Transport tire pressure and bearing check.',             60.00, '2026-10-18', NULL),
    (4, '2026-07-25', 'Engine Service',
        'Full engine service after planting season.',            385.00, NULL,         'No follow-up scheduled yet.'),
    (5, '2026-02-28', 'Belt / Chain Service',
        'Replaced pickup drive chain and adjusted tension.',     175.25, '2026-08-28', 'Overdue — machine is out of service.'),
    (5, '2026-06-02', 'Coolant Service',
        'Flushed and refilled coolant.',                          98.00, '2026-12-02', NULL);
