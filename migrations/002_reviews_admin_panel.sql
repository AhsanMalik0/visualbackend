-- ══════════════════════════════════════════════════════════════════════════
-- Migration 002: User Reviews & Admin Panel (API Service Configs)
-- ══════════════════════════════════════════════════════════════════════════

-- 1. USER REVIEWS TABLE
CREATE TABLE IF NOT EXISTS user_reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    review_text TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_reviews_user_id ON user_reviews(user_id);
CREATE INDEX IF NOT EXISTS idx_user_reviews_status ON user_reviews(status);

-- 2. API SERVICE CONFIGS TABLE
CREATE TABLE IF NOT EXISTS api_service_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    category VARCHAR(50) NOT NULL,
    last_toggled_by UUID REFERENCES users(id),
    last_toggled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Seed default API service configurations
INSERT INTO api_service_configs (service_name, display_name, is_active, category)
VALUES
    ('stripe', 'Stripe Payments', TRUE, 'payment'),
    ('nowpayments', 'NOWPayments Crypto', TRUE, 'payment'),
    ('gemini', 'Google Gemini AI', TRUE, 'ai'),
    ('kimi', 'Kimi AI (Moonshot)', TRUE, 'ai')
ON CONFLICT (service_name) DO NOTHING;
