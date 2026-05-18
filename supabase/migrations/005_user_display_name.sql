-- Store a user-facing name separate from the login username.
ALTER TABLE app_user
ADD COLUMN IF NOT EXISTS display_name VARCHAR(100);
