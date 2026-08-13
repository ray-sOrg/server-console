-- Exercise illustrations are structured JSON so each movement can have
-- start/finish images plus matching and attribution metadata.
ALTER TABLE fitness_exercise
    ADD COLUMN IF NOT EXISTS media JSONB;
