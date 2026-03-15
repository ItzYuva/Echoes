-- Echoes Phase 5: Users and Decisions tables
-- Supplements the existing Python-managed user_profiles table

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_token_hash VARCHAR(255) NOT NULL,
    intake_completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    query_id UUID,
    decision_text TEXT NOT NULL,
    decision_type VARCHAR(50),
    chosen_path VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    follow_up_at TIMESTAMPTZ,
    follow_up_sent BOOLEAN DEFAULT FALSE,
    reflection_received BOOLEAN DEFAULT FALSE,
    reflection_text TEXT,
    reflection_received_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_decisions_user ON decisions(user_id);
CREATE INDEX IF NOT EXISTS idx_decisions_follow_up ON decisions(follow_up_at) WHERE NOT follow_up_sent;

CREATE TABLE IF NOT EXISTS intake_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    is_complete BOOLEAN DEFAULT FALSE,
    turn_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_intake_sessions_user ON intake_sessions(user_id);
