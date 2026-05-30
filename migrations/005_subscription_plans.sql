-- Migration: Create subscription_plans table for admin-managed plans with feature restrictions
-- Run this against your database to create the table

CREATE TABLE IF NOT EXISTS subscription_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_key VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price_monthly FLOAT DEFAULT 0,
    price_yearly FLOAT DEFAULT 0,
    credits_per_month INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    is_popular BOOLEAN DEFAULT FALSE,

    -- Feature flags
    feature_lectures BOOLEAN DEFAULT TRUE,
    feature_quiz BOOLEAN DEFAULT TRUE,
    feature_summarize BOOLEAN DEFAULT TRUE,
    feature_research BOOLEAN DEFAULT FALSE,
    feature_groups BOOLEAN DEFAULT FALSE,
    feature_connections BOOLEAN DEFAULT FALSE,
    feature_messaging BOOLEAN DEFAULT FALSE,
    feature_study_rooms BOOLEAN DEFAULT FALSE,
    feature_analytics BOOLEAN DEFAULT FALSE,
    feature_3d_visuals BOOLEAN DEFAULT TRUE,
    feature_4d_animations BOOLEAN DEFAULT FALSE,
    feature_ppt BOOLEAN DEFAULT TRUE,
    feature_content_library BOOLEAN DEFAULT TRUE,
    feature_collaboration BOOLEAN DEFAULT FALSE,
    feature_api_access BOOLEAN DEFAULT FALSE,
    feature_batch_generation BOOLEAN DEFAULT FALSE,
    feature_hd_quality BOOLEAN DEFAULT FALSE,
    feature_priority_queue BOOLEAN DEFAULT FALSE,

    max_exports_per_day INTEGER DEFAULT 1,
    rate_limit VARCHAR(50) DEFAULT '10/hour',

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed default plans
INSERT INTO subscription_plans (plan_key, name, description, price_monthly, price_yearly, credits_per_month, sort_order, is_popular,
    feature_lectures, feature_quiz, feature_summarize, feature_research, feature_groups, feature_connections,
    feature_messaging, feature_study_rooms, feature_analytics, feature_3d_visuals, feature_4d_animations,
    feature_ppt, feature_content_library, feature_collaboration, feature_api_access, feature_batch_generation,
    feature_hd_quality, feature_priority_queue, max_exports_per_day, rate_limit)
VALUES
    ('free', 'Free', 'Get started with basic features', 0, 0, 10, 0, FALSE,
     TRUE, TRUE, TRUE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, TRUE, FALSE, TRUE, TRUE, FALSE, FALSE, FALSE, FALSE, FALSE, 1, '10/hour'),
    ('starter', 'Starter', 'For individual creators', 19, 190, 100, 1, FALSE,
     TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, FALSE, FALSE, TRUE, FALSE, TRUE, TRUE, FALSE, FALSE, FALSE, TRUE, FALSE, -1, '60/hour'),
    ('pro', 'Pro', 'For power users and teams', 49, 490, 500, 2, TRUE,
     TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, -1, '200/hour'),
    ('business', 'Business', 'For organizations', 149, 1490, 2000, 3, FALSE,
     TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, -1, '1000/hour')
ON CONFLICT (plan_key) DO NOTHING;
