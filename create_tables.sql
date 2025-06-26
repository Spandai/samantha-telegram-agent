-- Supabase tables for Samantha Telegram Agent
-- Run these commands in your Supabase SQL editor

-- 1. Conversations table (short-term memory)
CREATE TABLE IF NOT EXISTS conversations (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    message TEXT NOT NULL,
    is_user_message BOOLEAN NOT NULL DEFAULT true,
    tokens INTEGER DEFAULT 0,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    
    -- Indexes for performance
    INDEX idx_conversations_user_id (user_id),
    INDEX idx_conversations_timestamp (timestamp)
);

-- Enable Row Level Security
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

-- Policy to allow all operations (adjust based on your security needs)
CREATE POLICY "Allow all operations on conversations" ON conversations
    FOR ALL USING (true);

-- 2. Memory layers table (medium & long-term memory)
CREATE TABLE IF NOT EXISTS memory_layers (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE,
    short_term JSONB,
    medium_term TEXT,
    long_term JSONB,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Index for user lookups
    INDEX idx_memory_layers_user_id (user_id)
);

-- Enable Row Level Security
ALTER TABLE memory_layers ENABLE ROW LEVEL SECURITY;

-- Policy to allow all operations
CREATE POLICY "Allow all operations on memory_layers" ON memory_layers
    FOR ALL USING (true);

-- 3. Budget tracking table
CREATE TABLE IF NOT EXISTS budget_tracking (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd DECIMAL(10,6) NOT NULL DEFAULT 0,
    message_type TEXT DEFAULT 'chat',
    model TEXT DEFAULT 'gpt-4o-mini',
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    
    -- Indexes for performance
    INDEX idx_budget_tracking_user_id (user_id),
    INDEX idx_budget_tracking_timestamp (timestamp),
    INDEX idx_budget_tracking_user_date (user_id, DATE(timestamp))
);

-- Enable Row Level Security
ALTER TABLE budget_tracking ENABLE ROW LEVEL SECURITY;

-- Policy to allow all operations
CREATE POLICY "Allow all operations on budget_tracking" ON budget_tracking
    FOR ALL USING (true);

-- 4. Optional: Function to automatically update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to memory_layers table
CREATE TRIGGER update_memory_layers_updated_at 
    BEFORE UPDATE ON memory_layers 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- 5. View for daily budget summary (optional, for monitoring)
CREATE OR REPLACE VIEW daily_budget_summary AS
SELECT 
    user_id,
    DATE(timestamp) as date,
    COUNT(*) as total_messages,
    SUM(input_tokens) as total_input_tokens,
    SUM(output_tokens) as total_output_tokens,
    SUM(cost_usd) as total_cost_usd,
    AVG(cost_usd) as avg_cost_per_message
FROM budget_tracking 
GROUP BY user_id, DATE(timestamp)
ORDER BY user_id, date DESC;

-- 6. Cleanup function for old conversations (optional)
CREATE OR REPLACE FUNCTION cleanup_old_conversations(days_to_keep INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM conversations 
    WHERE timestamp < NOW() - INTERVAL '1 day' * days_to_keep;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Comments for documentation
COMMENT ON TABLE conversations IS 'Stores all conversation messages for short-term memory';
COMMENT ON TABLE memory_layers IS 'Stores user memory layers: medium-term summaries and long-term preferences';
COMMENT ON TABLE budget_tracking IS 'Tracks OpenAI API usage and costs per user';
COMMENT ON VIEW daily_budget_summary IS 'Daily aggregated budget and usage statistics';
COMMENT ON FUNCTION cleanup_old_conversations IS 'Cleanup function to remove old conversation data';

-- Success message
SELECT 'Samantha database tables created successfully!' as result;