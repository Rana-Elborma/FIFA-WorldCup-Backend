-- 0. Stadium
create table if not exists stadium (
  stadium_id int primary key,
  name text not null,
  city text,
  capacity int
);

-- 1. Zone
create table if not exists zone (
  zone_id int primary key,
  stadium_id int references stadium(stadium_id),
  name text,
  area_m2 float
);

-- 2. Update gate (link to zone + stadium)
alter table gate
add column if not exists stadium_id int references stadium(stadium_id),
add column if not exists zone_id int references zone(zone_id);

-- 3. Audit log (SYSTEM LOGS ✅ requirement)
create table if not exists audit_log (
  log_id bigserial primary key,
  ts timestamptz default now(),
  user_id uuid,
  action text,
  result text
);