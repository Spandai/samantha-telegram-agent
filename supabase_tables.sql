-- Tables pour Samantha Bot
-- À exécuter dans Supabase SQL Editor

-- Table conversations
CREATE TABLE IF NOT EXISTS conversations (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    message TEXT NOT NULL,
    is_user BOOLEAN NOT NULL DEFAULT true,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Table memory (stockage clé-valeur)
CREATE TABLE IF NOT EXISTS memory (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, key)
);

-- Table budget
CREATE TABLE IF NOT EXISTS budget (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    cost REAL NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour performance
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON conversations(timestamp);
CREATE INDEX IF NOT EXISTS idx_memory_user_id ON memory(user_id);
CREATE INDEX IF NOT EXISTS idx_budget_user_id ON budget(user_id);
CREATE INDEX IF NOT EXISTS idx_budget_timestamp ON budget(timestamp);