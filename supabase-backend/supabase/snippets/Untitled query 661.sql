-- 1. Enable RLS
alter table alert enable row level security;

-- 2. Allow anon to read (required for Realtime to push to client)
create policy "anon read alert"
  on alert for select
  to anon
  using (true);

-- 3. Allow anon to insert
create policy "anon insert alert"
  on alert for insert
  to anon
  with check (true);