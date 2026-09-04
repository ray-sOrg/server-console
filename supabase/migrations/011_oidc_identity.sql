ALTER TABLE app_user
ADD COLUMN IF NOT EXISTS oidc_subject VARCHAR(255);

CREATE UNIQUE INDEX IF NOT EXISTS idx_app_user_oidc_subject
ON app_user(oidc_subject)
WHERE oidc_subject IS NOT NULL;

CREATE TABLE IF NOT EXISTS oidc_login_attempt (
    state_hash VARCHAR(64) PRIMARY KEY,
    code_verifier VARCHAR(128) NOT NULL,
    nonce VARCHAR(128) NOT NULL,
    target_app VARCHAR(20) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_oidc_login_attempt_expires_at
ON oidc_login_attempt(expires_at);

