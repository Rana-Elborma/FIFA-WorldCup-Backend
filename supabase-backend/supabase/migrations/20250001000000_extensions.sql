-- ============================================================
-- Migration 0: Extensions
-- ============================================================
create extension if not exists pgcrypto;   -- AES-256, SHA-256, gen_random_uuid
create extension if not exists "uuid-ossp"; -- uuid_generate_v4 fallback

-- NOTE: The AES-256 key (app.aes_key) is set in config.toml under [db.settings].
-- In production: move the key to Supabase Vault (Dashboard → Vault).
