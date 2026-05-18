-- Store the user's height for BMI calculations in weight-management.
ALTER TABLE app_user
ADD COLUMN IF NOT EXISTS height_cm INTEGER
CHECK (height_cm IS NULL OR height_cm BETWEEN 80 AND 250);
