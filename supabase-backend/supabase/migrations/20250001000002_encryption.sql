-- ============================================================
-- Migration 2: AES-256 encryption helpers for PII columns
-- All GPS coordinates are stored encrypted; only service-role
-- functions can decrypt them.
-- ============================================================

-- ── AES key resolver ─────────────────────────────────────────
-- Uses app.aes_key if set (production via superuser), otherwise
-- falls back to the local-dev key below.
-- ⚠ In production: run  ALTER DATABASE postgres SET app.aes_key='...'
--   as a superuser BEFORE deploying, or use Supabase Vault.
create or replace function _aes_key()
  returns text
  language sql
  security definer
  stable
as $$
  select coalesce(
    nullif(current_setting('app.aes_key', true), ''),
    'AramcoStadium@AES256Key!Local32!!'   -- 32 chars, local dev only
  );
$$;

-- ── Helper: encrypt a float with AES-256 ─────────────────────
create or replace function enc_float(p_value float)
  returns bytea
  language sql
  security definer
  stable
as $$
  select pgp_sym_encrypt(
    p_value::text,
    _aes_key(),
    'cipher-algo=aes256'
  );
$$;

-- ── Helper: decrypt a bytea back to float ────────────────────
create or replace function dec_float(p_cipher bytea)
  returns float
  language sql
  security definer
  stable
as $$
  select pgp_sym_decrypt(
    p_cipher,
    _aes_key()
  )::float;
$$;

-- ── Helper: one-way SHA-256 hash for session identifiers ─────
create or replace function hash_session(p_session_id text)
  returns text
  language sql
  immutable
as $$
  select encode(digest(p_session_id, 'sha256'), 'hex');
$$;

-- ── Secure INSERT function for GPS events ────────────────────
-- Mobile app calls this RPC; raw coordinates never leave the DB
-- without the service-role key.
create or replace function insert_gps_event(
  p_latitude       float,
  p_longitude      float,
  p_stadium_id     int,
  p_zone_id        int,
  p_nearest_gate_id int,
  p_session_id     text
)
  returns bigint
  language plpgsql
  security definer
as $$
declare
  v_id bigint;
begin
  insert into gps_event (
    latitude_enc, longitude_enc,
    stadium_id, zone_id, nearest_gate_id,
    session_hash
  ) values (
    enc_float(p_latitude),
    enc_float(p_longitude),
    p_stadium_id,
    p_zone_id,
    p_nearest_gate_id,
    hash_session(p_session_id)
  )
  returning gps_event_id into v_id;

  return v_id;
end;
$$;

-- ── Decrypted view (service-role only, RLS will block anon) ──
create or replace view gps_event_decrypted as
select
  gps_event_id,
  ts,
  dec_float(latitude_enc)  as latitude,
  dec_float(longitude_enc) as longitude,
  stadium_id,
  zone_id,
  nearest_gate_id,
  session_hash
from gps_event;

-- Revoke direct table access; only the RPC function is the API
revoke all on gps_event from anon, authenticated;
grant execute on function insert_gps_event to anon, authenticated;
