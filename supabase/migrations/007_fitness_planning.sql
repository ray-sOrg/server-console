-- Phase 1 fitness module: reusable exercises and editable weekly plans.
CREATE TABLE IF NOT EXISTS fitness_exercise (
    id BIGSERIAL PRIMARY KEY,
    user_identity VARCHAR(100) NOT NULL,
    name VARCHAR(120) NOT NULL,
    category VARCHAR(20) NOT NULL DEFAULT 'strength'
        CHECK (category IN ('strength', 'skill', 'cardio', 'mobility', 'recovery')),
    primary_muscle VARCHAR(80),
    secondary_muscles TEXT,
    equipment VARCHAR(160),
    metric_type VARCHAR(20) NOT NULL DEFAULT 'reps'
        CHECK (metric_type IN ('reps', 'duration', 'distance', 'check')),
    instructions TEXT,
    cautions TEXT,
    progression_notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_fitness_exercise_user_name UNIQUE (user_identity, name)
);

CREATE INDEX IF NOT EXISTS idx_fitness_exercise_user_identity
    ON fitness_exercise(user_identity);
CREATE INDEX IF NOT EXISTS idx_fitness_exercise_user_active
    ON fitness_exercise(user_identity, is_active);

CREATE TABLE IF NOT EXISTS fitness_plan (
    id BIGSERIAL PRIMARY KEY,
    user_identity VARCHAR(100) NOT NULL,
    tracked_person_id INTEGER REFERENCES tracked_person(id) ON DELETE SET NULL,
    name VARCHAR(120) NOT NULL,
    description TEXT,
    duration_weeks INTEGER NOT NULL DEFAULT 12 CHECK (duration_weeks BETWEEN 1 AND 104),
    start_date DATE,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fitness_plan_user_identity ON fitness_plan(user_identity);
CREATE INDEX IF NOT EXISTS idx_fitness_plan_tracked_person_id ON fitness_plan(tracked_person_id);
CREATE INDEX IF NOT EXISTS idx_fitness_plan_user_active ON fitness_plan(user_identity, is_active);

CREATE TABLE IF NOT EXISTS fitness_plan_day (
    id BIGSERIAL PRIMARY KEY,
    plan_id BIGINT NOT NULL REFERENCES fitness_plan(id) ON DELETE CASCADE,
    weekday SMALLINT NOT NULL CHECK (weekday BETWEEN 1 AND 7),
    name VARCHAR(120) NOT NULL,
    focus VARCHAR(160),
    is_rest BOOLEAN NOT NULL DEFAULT FALSE,
    estimated_minutes INTEGER CHECK (estimated_minutes BETWEEN 0 AND 480),
    notes TEXT,
    CONSTRAINT uq_fitness_plan_day_weekday UNIQUE (plan_id, weekday)
);

CREATE INDEX IF NOT EXISTS idx_fitness_plan_day_plan_id ON fitness_plan_day(plan_id);

CREATE TABLE IF NOT EXISTS fitness_plan_exercise (
    id BIGSERIAL PRIMARY KEY,
    plan_day_id BIGINT NOT NULL REFERENCES fitness_plan_day(id) ON DELETE CASCADE,
    exercise_id BIGINT NOT NULL REFERENCES fitness_exercise(id) ON DELETE RESTRICT,
    sort_order INTEGER NOT NULL CHECK (sort_order > 0),
    sets INTEGER CHECK (sets BETWEEN 1 AND 20),
    reps_min INTEGER,
    reps_max INTEGER,
    duration_seconds_min INTEGER,
    duration_seconds_max INTEGER,
    rir_min INTEGER,
    rir_max INTEGER,
    target_weight_kg NUMERIC(7, 2),
    weight_note TEXT,
    rest_seconds INTEGER CHECK (rest_seconds BETWEEN 0 AND 3600),
    progression_type VARCHAR(60),
    plan_notes TEXT,
    superset_group VARCHAR(20),
    each_side BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_fitness_plan_exercise_order UNIQUE (plan_day_id, sort_order)
);

CREATE INDEX IF NOT EXISTS idx_fitness_plan_exercise_plan_day_id
    ON fitness_plan_exercise(plan_day_id);
CREATE INDEX IF NOT EXISTS idx_fitness_plan_exercise_exercise_id
    ON fitness_plan_exercise(exercise_id);
