-- Track multiple people under one login account for family weight records.
CREATE TABLE IF NOT EXISTS tracked_person (
    id SERIAL PRIMARY KEY,
    user_identity VARCHAR(100) NOT NULL,
    name VARCHAR(100) NOT NULL,
    height_cm INTEGER NOT NULL CHECK (height_cm BETWEEN 80 AND 250),
    birth_date DATE,
    relationship VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tracked_person_user_identity ON tracked_person(user_identity);

ALTER TABLE weight_record
ADD COLUMN IF NOT EXISTS tracked_person_id INTEGER;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'weight_record_tracked_person_id_fkey'
    ) THEN
        ALTER TABLE weight_record
        ADD CONSTRAINT weight_record_tracked_person_id_fkey
        FOREIGN KEY (tracked_person_id) REFERENCES tracked_person(id)
        ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_weight_record_tracked_person_id ON weight_record(tracked_person_id);
