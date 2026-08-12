-- Persistent, revocable login sessions for long-lived refresh tokens.
CREATE TABLE IF NOT EXISTS auth_session (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL UNIQUE,
    user_identity VARCHAR(100) NOT NULL
        REFERENCES app_user(username) ON DELETE CASCADE,
    current_refresh_jti VARCHAR(64) UNIQUE,
    previous_refresh_jti VARCHAR(64),
    refresh_rotated_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_auth_session_user_identity
    ON auth_session(user_identity);
CREATE INDEX IF NOT EXISTS idx_auth_session_expires_at
    ON auth_session(expires_at);
CREATE INDEX IF NOT EXISTS idx_auth_session_revoked_at
    ON auth_session(revoked_at);
CREATE INDEX IF NOT EXISTS idx_auth_session_user_active
    ON auth_session(user_identity, expires_at)
    WHERE revoked_at IS NULL;
