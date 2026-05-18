-- Store the user's birth date for account profile display.
ALTER TABLE app_user
ADD COLUMN IF NOT EXISTS birth_date DATE;
