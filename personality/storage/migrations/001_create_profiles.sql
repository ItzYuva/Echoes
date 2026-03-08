-- Echoes Phase 2 -- Profile Storage Schema
-- PostgreSQL migration: creates user_profiles and profile_versions tables
-- Idempotent: safe to run multiple times

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Main user profiles table
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Values vector (stored as individual columns for queryability)
    risk_tolerance FLOAT NOT NULL CHECK (risk_tolerance BETWEEN 0 AND 1),
    change_orientation FLOAT NOT NULL CHECK (change_orientation BETWEEN 0 AND 1),
    security_vs_growth FLOAT NOT NULL CHECK (security_vs_growth BETWEEN 0 AND 1),
    action_bias FLOAT NOT NULL CHECK (action_bias BETWEEN 0 AND 1),
    social_weight FLOAT NOT NULL CHECK (social_weight BETWEEN 0 AND 1),
    time_horizon FLOAT NOT NULL CHECK (time_horizon BETWEEN 0 AND 1),
    loss_sensitivity FLOAT NOT NULL CHECK (loss_sensitivity BETWEEN 0 AND 1),
    ambiguity_tolerance FLOAT NOT NULL CHECK (ambiguity_tolerance BETWEEN 0 AND 1),

    -- Metadata
    confidence_notes JSONB DEFAULT '{}',
    intake_version INT NOT NULL DEFAULT 1,
    intake_turns INT NOT NULL,
    intake_duration_seconds INT DEFAULT 0,
    profile_version INT NOT NULL DEFAULT 1,

    -- The full intake transcript (for debugging and future analysis)
    intake_transcript JSONB NOT NULL DEFAULT '[]'
);

-- Historical profile versions for tracking evolution
CREATE TABLE IF NOT EXISTS profile_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    version INT NOT NULL,
    values_snapshot JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source TEXT NOT NULL,  -- 'intake', 'follow_up', 'manual_update'

    UNIQUE(user_id, version)
);

-- Indexes for Phase 3: finding users with similar profiles
CREATE INDEX IF NOT EXISTS idx_values_risk ON user_profiles(risk_tolerance);
CREATE INDEX IF NOT EXISTS idx_values_change ON user_profiles(change_orientation);
CREATE INDEX IF NOT EXISTS idx_values_security ON user_profiles(security_vs_growth);
CREATE INDEX IF NOT EXISTS idx_values_action ON user_profiles(action_bias);
CREATE INDEX IF NOT EXISTS idx_values_social ON user_profiles(social_weight);
CREATE INDEX IF NOT EXISTS idx_values_time ON user_profiles(time_horizon);
CREATE INDEX IF NOT EXISTS idx_values_loss ON user_profiles(loss_sensitivity);
CREATE INDEX IF NOT EXISTS idx_values_ambiguity ON user_profiles(ambiguity_tolerance);

-- Index for profile version lookups
CREATE INDEX IF NOT EXISTS idx_profile_versions_user ON profile_versions(user_id, version);
