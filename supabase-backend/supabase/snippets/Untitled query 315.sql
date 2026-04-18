-- Switch to anon role so Realtime fires properly
insert into alert (gate_id, severity, reason)
values (2, 'HIGH', 'Test alert from anon');