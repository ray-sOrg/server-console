-- ========================================
-- Weight Management Schema for server-console
-- ========================================

CREATE TABLE IF NOT EXISTS weight_record (
    id SERIAL PRIMARY KEY,
    user_identity VARCHAR(100) NOT NULL,
    tracked_person_id INTEGER,
    weight NUMERIC(6, 2) NOT NULL,
    record_date DATE NOT NULL,
    body_fat NUMERIC(5, 2),
    bmi NUMERIC(5, 2),
    note TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_weight_record_user_identity ON weight_record(user_identity);
CREATE INDEX IF NOT EXISTS idx_weight_record_tracked_person_id ON weight_record(tracked_person_id);
CREATE INDEX IF NOT EXISTS idx_weight_record_record_date ON weight_record(record_date);
CREATE INDEX IF NOT EXISTS idx_weight_record_user_date ON weight_record(user_identity, record_date DESC);

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_weight_record_updated_at ON weight_record;
CREATE TRIGGER update_weight_record_updated_at
    BEFORE UPDATE ON weight_record
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
