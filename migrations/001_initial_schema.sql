-- Membot Core Schema for Supabase
-- Created: 2025-01-XX
-- Purpose: Store hypotheses, events, and system state

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Health check table (for connection verification)
CREATE TABLE IF NOT EXISTS _membot_health_check (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    status TEXT NOT NULL DEFAULT 'healthy',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert initial health record
INSERT INTO _membot_health_check (status) VALUES ('healthy')
ON CONFLICT DO NOTHING;

-- Hypotheses table: stores all active and historical hypotheses
CREATE TABLE IF NOT EXISTS membot_hypotheses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hypothesis_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    probability FLOAT DEFAULT 0.5 CHECK (probability >= 0 AND probability <= 1),
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'confirmed', 'rejected', 'paused')),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast hypothesis lookups
CREATE INDEX IF NOT EXISTS idx_hypotheses_id ON membot_hypotheses(hypothesis_id);
CREATE INDEX IF NOT EXISTS idx_hypotheses_status ON membot_hypotheses(status);
CREATE INDEX IF NOT EXISTS idx_hypotheses_probability ON membot_hypotheses(probability DESC);

-- Events table: immutable log of all system events
CREATE TABLE IF NOT EXISTS membot_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type TEXT NOT NULL,
    payload JSONB DEFAULT '{}',
    source TEXT DEFAULT 'membot',
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    processed BOOLEAN DEFAULT FALSE
);

-- Indexes for event querying
CREATE INDEX IF NOT EXISTS idx_events_type ON membot_events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON membot_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_processed ON membot_events(processed) WHERE processed = FALSE;

-- Observer gate alerts table
CREATE TABLE IF NOT EXISTS membot_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hypothesis_id TEXT REFERENCES membot_hypotheses(hypothesis_id),
    alert_type TEXT NOT NULL,
    threshold_crossed FLOAT,
    current_value FLOAT,
    message TEXT,
    acknowledged BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alerts_hypothesis ON membot_alerts(hypothesis_id);
CREATE INDEX IF NOT EXISTS idx_alerts_acknowledged ON membot_alerts(acknowledged) WHERE acknowledged = FALSE;

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for auto-updating updated_at on hypotheses
DROP TRIGGER IF EXISTS update_hypotheses_updated_at ON membot_hypotheses;
CREATE TRIGGER update_hypotheses_updated_at
    BEFORE UPDATE ON membot_hypotheses
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS) policies
-- Note: In production, enable RLS and define specific policies
-- ALTER TABLE membot_hypotheses ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE membot_events ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE membot_alerts ENABLE ROW LEVEL SECURITY;

-- Sample policy (commented out - enable in production with proper auth)
-- CREATE POLICY "Allow authenticated users to read hypotheses"
--     ON membot_hypotheses FOR SELECT
--     USING (auth.role() = 'authenticated');

COMMENT ON TABLE membot_hypotheses IS 'Stores all membot hypotheses with Bayesian probabilities';
COMMENT ON TABLE membot_events IS 'Immutable event log for system auditing and analytics';
COMMENT ON TABLE membot_alerts IS 'Observer gate alerts for hypothesis threshold crossings';
