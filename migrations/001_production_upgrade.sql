-- Migration: Production Upgrade v2.0
-- Adds subscription tracking, API keys, templates, usage logging

-- 1. Add new columns to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR;
ALTER TABLE users ADD COLUMN IF NOT EXISTS api_key VARCHAR UNIQUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS api_key_created_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS total_generations INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_generation_at TIMESTAMPTZ;

-- Update default plan value
ALTER TABLE users ALTER COLUMN plan SET DEFAULT 'free';

-- 2. Create subscriptions table
CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    plan VARCHAR NOT NULL DEFAULT 'free',
    status VARCHAR NOT NULL DEFAULT 'active',
    stripe_subscription_id VARCHAR,
    stripe_customer_id VARCHAR,
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe_id ON subscriptions(stripe_subscription_id);

-- 3. Add stripe_payment_id to payments table
ALTER TABLE payments ADD COLUMN IF NOT EXISTS stripe_payment_id VARCHAR;
CREATE INDEX IF NOT EXISTS idx_payments_stripe_id ON payments(stripe_payment_id);

-- 4. Add new columns to visualizations table
ALTER TABLE visualizations ADD COLUMN IF NOT EXISTS generation_type VARCHAR(50) DEFAULT '3d_visual';
ALTER TABLE visualizations ADD COLUMN IF NOT EXISTS quality VARCHAR(20) DEFAULT 'standard';
ALTER TABLE visualizations ADD COLUMN IF NOT EXISTS export_format VARCHAR(20);
ALTER TABLE visualizations ADD COLUMN IF NOT EXISTS export_url TEXT;
ALTER TABLE visualizations ADD COLUMN IF NOT EXISTS thumbnail_url TEXT;
ALTER TABLE visualizations ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT FALSE;
ALTER TABLE visualizations ADD COLUMN IF NOT EXISTS view_count INTEGER DEFAULT 0;
ALTER TABLE visualizations ADD COLUMN IF NOT EXISTS like_count INTEGER DEFAULT 0;

-- 5. Create templates table
CREATE TABLE IF NOT EXISTS templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(100) NOT NULL,
    thumbnail_url TEXT,
    html_template TEXT NOT NULL,
    parameters JSONB,
    is_premium BOOLEAN DEFAULT FALSE,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_templates_category ON templates(category);

-- 6. Create API usage logs table
CREATE TABLE IF NOT EXISTS api_usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    endpoint VARCHAR NOT NULL,
    method VARCHAR(10) NOT NULL,
    credits_used INTEGER DEFAULT 0,
    response_status INTEGER,
    generation_type VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_api_usage_user_id ON api_usage_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_api_usage_created_at ON api_usage_logs(created_at);

-- 7. Update existing users plan names (Free -> free, Pro -> pro)
UPDATE users SET plan = LOWER(plan) WHERE plan != LOWER(plan);
