-- Echoes Phase 4 -- Agent Activity Logs
-- Tracks every agent invocation: trigger context, tool calls, results, and performance.

CREATE TABLE IF NOT EXISTS agent_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_log_id UUID REFERENCES query_logs(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Trigger context
    trigger_confidence_level TEXT NOT NULL,
    trigger_confidence_score FLOAT NOT NULL,
    trigger_reasons JSONB,

    -- Agent activity
    tool_calls_made INT NOT NULL,
    tools_used JSONB NOT NULL,
    total_candidates_found INT NOT NULL,
    validated_count INT NOT NULL,
    rejected_count INT NOT NULL,

    -- Results
    stories_returned INT NOT NULL,
    stories_added_to_db INT NOT NULL DEFAULT 0,
    sources JSONB NOT NULL,

    -- Performance
    total_latency_ms INT,
    search_latency_ms INT,
    validation_latency_ms INT,
    tokens_used INT,

    -- Outcome
    confidence_before FLOAT,
    confidence_after FLOAT,
    confidence_improvement FLOAT
);

CREATE INDEX IF NOT EXISTS idx_agent_trigger ON agent_logs(trigger_confidence_level);
CREATE INDEX IF NOT EXISTS idx_agent_improvement ON agent_logs(confidence_improvement);
CREATE INDEX IF NOT EXISTS idx_agent_created ON agent_logs(created_at);
