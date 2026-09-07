ALTER TABLE auth_session ADD COLUMN IF NOT EXISTS oidc_sid VARCHAR(255);
ALTER TABLE auth_session ADD COLUMN IF NOT EXISTS oidc_subject VARCHAR(255);
CREATE INDEX IF NOT EXISTS ix_auth_session_oidc_sid ON auth_session (oidc_sid);
