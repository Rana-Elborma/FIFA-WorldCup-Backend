-- ============================================================
-- Seed: realistic test data for Aramco Stadium
-- Run automatically on: supabase db reset
-- ============================================================

-- ── Stadium ──────────────────────────────────────────────────
insert into stadium (stadium_id, name, city, capacity)
values (1, 'Aramco Stadium', 'Dhahran', 45000)
on conflict do nothing;

-- ── Zones ────────────────────────────────────────────────────
insert into zone (zone_id, stadium_id, name, area_m2)
values
  (1, 1, 'North Entrance', 120),
  (2, 1, 'South Entrance', 110),
  (3, 1, 'East Entrance',  100),
  (4, 1, 'West Entrance',   95)
on conflict do nothing;

-- ── Gates ────────────────────────────────────────────────────
insert into gate (gate_id, zone_id, name, is_open)
values
  (1, 1, 'Gate 1', true),
  (2, 2, 'Gate 2', true),
  (3, 3, 'Gate 3', true),
  (4, 4, 'Gate 4', true)
on conflict do nothing;

-- ── Metric windows (encrypted via RPC — plain values never stored) ──
select insert_metric_window(1, 1, 1, 1800000, 14, 4,  12.5);
select insert_metric_window(1, 2, 2, 1200000,  8, 2,   7.8);
select insert_metric_window(1, 3, 3, 4200000, 32, 18, 28.0);
select insert_metric_window(1, 4, 4, 2800000, 22, 10, 19.5);

-- ── Predictions (encrypted via RPC) ─────────────────────────
select insert_prediction(1, 1, 1, 1.8, 6.0,  0.18, 0.91, 'LOW',    15);
select insert_prediction(1, 2, 2, 1.2, 1.0,  0.08, 0.95, 'LOW',    15);
select insert_prediction(1, 3, 3, 4.2, 14.5, 0.82, 0.88, 'HIGH',   15);
select insert_prediction(1, 4, 4, 2.8, 7.0,  0.45, 0.84, 'MEDIUM', 15);

-- ── Active alert for Gate 3 (encrypted via RPC) ──────────────
select insert_alert(1, 3, 3, 'HIGH', 'Density exceeds safe threshold at Gate 3 area');
