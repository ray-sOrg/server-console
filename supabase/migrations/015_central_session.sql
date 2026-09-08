ALTER TABLE auth_session ADD COLUMN IF NOT EXISTS oidc_refresh_token TEXT;
ALTER TABLE auth_session ADD COLUMN IF NOT EXISTS oidc_checked_at TIMESTAMPTZ;
