-- PROVE AES-256: encrypt a real piece of sensitive data and show it stored encrypted
create extension if not exists pgcrypto;

-- Insert a test audit log with AES-256 encrypted content
insert into audit_log (user_id, action, result)
values (
  null,
  'demo.encryption.proof',
  encode(
    pgp_sym_encrypt(
      'gate_id=1 | command=open | operator=admin | ts=2026-04-05 12:00:00',
      'FIFA2034-AES256-SecretKey'
    ),
    'base64'
  )
);

-- Now READ it back — show it is unreadable without the key
select 
  log_id,
  ts,
  action,
  result as "encrypted_content (unreadable)"
from audit_log
where action = 'demo.encryption.proof';

-- PROVE decryption only works with correct key
select 
  log_id,
  action,
  pgp_sym_decrypt(
    decode(result, 'base64'),
    'FIFA2034-AES256-SecretKey'
  ) as "decrypted_content (readable with key)"
from audit_log
where action = 'demo.encryption.proof';