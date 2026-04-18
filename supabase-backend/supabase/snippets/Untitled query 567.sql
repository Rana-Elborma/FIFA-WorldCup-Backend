-- 1. Gates table
create table if not exists gate (
  gate_id int primary key,
  name text not null,
  zone_area_m2 float default 60,
  is_open bool default false
);

-- 2. Metric windows (raw crowd data every 15 sec)
create table if not exists metric_window (
  window_id bigserial primary key,
  gate_id int references gate(gate_id),
  ts timestamptz default now(),
  density_ppm float,
  arrivals_per_min float,
  queue_len_est int
);

-- 3. AI predictions (wait time forecast)
create table if not exists prediction (
  pred_id bigserial primary key,
  gate_id int references gate(gate_id),
  ts timestamptz default now(),
  wait_pred_min float,
  congestion_prob float,
  severity text check (severity in ('LOW','MEDIUM','HIGH')),
  horizon_min int default 15
);

-- 4. Alerts (triggered when density spikes)
create table if not exists alert (
  alert_id bigserial primary key,
  gate_id int references gate(gate_id),
  ts timestamptz default now(),
  severity text check (severity in ('LOW','MEDIUM','HIGH')),
  reason text
);

-- 5. Gate commands (dashboard sends, Pi receives)
create table if not exists gate_command (
  cmd_id bigserial primary key,
  gate_id int references gate(gate_id),
  ts timestamptz default now(),
  command text check (command in ('open','close')),
  ack_status text default 'pending',
  ack_ts timestamptz
);

-- Enable Realtime on alert and gate_command
alter publication supabase_realtime add table alert;
alter publication supabase_realtime add table gate_command;

-- Seed test data
insert into gate (gate_id, name, zone_area_m2) 
values (1, 'Gate A', 60), (2, 'Gate B', 60)
on conflict do nothing;

insert into prediction (gate_id, wait_pred_min, congestion_prob, severity)
values (1, 3.5, 0.2, 'LOW'), (2, 8.2, 0.75, 'HIGH');

insert into metric_window (gate_id, density_ppm, arrivals_per_min, queue_len_est)
values (1, 2000000, 18, 5), (2, 4500000, 35, 22);