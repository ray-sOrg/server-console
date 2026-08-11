-- Phase 4 fitness module: workout readiness, effort and pain feedback.
ALTER TABLE fitness_session
    ADD COLUMN IF NOT EXISTS readiness_score SMALLINT
        CHECK (readiness_score BETWEEN 1 AND 5),
    ADD COLUMN IF NOT EXISTS effort_score SMALLINT
        CHECK (effort_score BETWEEN 1 AND 10),
    ADD COLUMN IF NOT EXISTS pain_flag BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS pain_notes TEXT;
