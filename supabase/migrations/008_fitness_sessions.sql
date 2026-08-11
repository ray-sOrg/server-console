-- Phase 2 fitness module: immutable workout snapshots and per-set check-ins.
CREATE TABLE IF NOT EXISTS fitness_session (
    id BIGSERIAL PRIMARY KEY,
    user_identity VARCHAR(100) NOT NULL,
    subject_key VARCHAR(120) NOT NULL DEFAULT 'self',
    tracked_person_id INTEGER REFERENCES tracked_person(id) ON DELETE SET NULL,
    plan_id BIGINT REFERENCES fitness_plan(id) ON DELETE SET NULL,
    plan_day_id BIGINT REFERENCES fitness_plan_day(id) ON DELETE SET NULL,
    scheduled_date DATE NOT NULL,
    weekday SMALLINT NOT NULL CHECK (weekday BETWEEN 1 AND 7),
    name VARCHAR(120) NOT NULL,
    focus VARCHAR(160),
    status VARCHAR(20) NOT NULL DEFAULT 'in_progress'
        CHECK (status IN ('in_progress', 'completed', 'partial', 'skipped')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_fitness_session_user_subject_date
        UNIQUE (user_identity, subject_key, scheduled_date)
);

CREATE INDEX IF NOT EXISTS idx_fitness_session_user_identity ON fitness_session(user_identity);
CREATE INDEX IF NOT EXISTS idx_fitness_session_tracked_person_id ON fitness_session(tracked_person_id);
CREATE INDEX IF NOT EXISTS idx_fitness_session_plan_id ON fitness_session(plan_id);
CREATE INDEX IF NOT EXISTS idx_fitness_session_plan_day_id ON fitness_session(plan_day_id);
CREATE INDEX IF NOT EXISTS idx_fitness_session_user_date
    ON fitness_session(user_identity, scheduled_date DESC);
CREATE INDEX IF NOT EXISTS idx_fitness_session_user_status
    ON fitness_session(user_identity, status);

CREATE TABLE IF NOT EXISTS fitness_session_exercise (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGINT NOT NULL REFERENCES fitness_session(id) ON DELETE CASCADE,
    source_plan_exercise_id BIGINT REFERENCES fitness_plan_exercise(id) ON DELETE SET NULL,
    exercise_id BIGINT REFERENCES fitness_exercise(id) ON DELETE SET NULL,
    sort_order INTEGER NOT NULL CHECK (sort_order > 0),
    exercise_name VARCHAR(120) NOT NULL,
    category VARCHAR(20) NOT NULL,
    primary_muscle VARCHAR(80),
    equipment VARCHAR(160),
    metric_type VARCHAR(20) NOT NULL
        CHECK (metric_type IN ('reps', 'duration', 'distance', 'check')),
    instructions TEXT,
    cautions TEXT,
    target_sets INTEGER,
    reps_min INTEGER,
    reps_max INTEGER,
    duration_seconds_min INTEGER,
    duration_seconds_max INTEGER,
    rir_min INTEGER,
    rir_max INTEGER,
    target_weight_kg NUMERIC(7, 2),
    weight_note TEXT,
    rest_seconds INTEGER,
    progression_type VARCHAR(60),
    plan_notes TEXT,
    superset_group VARCHAR(20),
    each_side BOOLEAN NOT NULL DEFAULT FALSE,
    completed BOOLEAN NOT NULL DEFAULT FALSE,
    notes TEXT,
    CONSTRAINT uq_fitness_session_exercise_order UNIQUE (session_id, sort_order)
);

CREATE INDEX IF NOT EXISTS idx_fitness_session_exercise_session_id
    ON fitness_session_exercise(session_id);
CREATE INDEX IF NOT EXISTS idx_fitness_session_exercise_source_plan_id
    ON fitness_session_exercise(source_plan_exercise_id);
CREATE INDEX IF NOT EXISTS idx_fitness_session_exercise_exercise_id
    ON fitness_session_exercise(exercise_id);

CREATE TABLE IF NOT EXISTS fitness_set (
    id BIGSERIAL PRIMARY KEY,
    session_exercise_id BIGINT NOT NULL
        REFERENCES fitness_session_exercise(id) ON DELETE CASCADE,
    set_number INTEGER NOT NULL CHECK (set_number > 0),
    actual_reps INTEGER CHECK (actual_reps >= 0),
    actual_duration_seconds INTEGER CHECK (actual_duration_seconds >= 0),
    actual_weight_kg NUMERIC(7, 2) CHECK (actual_weight_kg >= 0),
    rir INTEGER CHECK (rir BETWEEN 0 AND 10),
    completed BOOLEAN NOT NULL DEFAULT FALSE,
    completed_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_fitness_set_exercise_number UNIQUE (session_exercise_id, set_number)
);

CREATE INDEX IF NOT EXISTS idx_fitness_set_session_exercise_id
    ON fitness_set(session_exercise_id);
CREATE INDEX IF NOT EXISTS idx_fitness_set_completed
    ON fitness_set(session_exercise_id, completed);
