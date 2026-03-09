-- ============================================================
-- Echoes Phase 3 -- Query Logs Table
--
-- Stores every user query with confidence scores, stories shown,
-- and latency metrics. This is the primary diagnostic tool for
-- understanding system quality and data gaps.
-- ============================================================

CREATE TABLE IF NOT EXISTS query_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES user_profiles(user_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Input
    query_text TEXT NOT NULL,
    query_analysis JSONB NOT NULL DEFAULT '{}',

    -- Retrieval
    candidates_found INT NOT NULL DEFAULT 0,
    stories_presented INT NOT NULL DEFAULT 0,
    story_ids JSONB NOT NULL DEFAULT '[]',

    -- Confidence
    confidence_score FLOAT NOT NULL DEFAULT 0.0,
    confidence_level TEXT NOT NULL DEFAULT 'insufficient',
    confidence_reasons JSONB DEFAULT '[]',

    -- Performance
    total_latency_ms INT DEFAULT 0,
    embedding_latency_ms INT DEFAULT 0,
    retrieval_latency_ms INT DEFAULT 0,
    reranking_latency_ms INT DEFAULT 0,
    presentation_latency_ms INT DEFAULT 0,
    tokens_input INT DEFAULT 0,
    tokens_output INT DEFAULT 0,

    -- For Phase 6
    decision_logged BOOLEAN DEFAULT FALSE,
    decision_id UUID DEFAULT NULL
);

-- ── Indexes ─────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_query_confidence
    ON query_logs(confidence_level);

CREATE INDEX IF NOT EXISTS idx_query_user
    ON query_logs(user_id);

CREATE INDEX IF NOT EXISTS idx_query_created
    ON query_logs(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_query_decision_type
    ON query_logs((query_analysis->>'decision_type'));
