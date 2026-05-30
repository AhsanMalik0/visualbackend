CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    plan VARCHAR(255) NOT NULL DEFAULT 'Free',
    credits INTEGER NOT NULL DEFAULT 0,
    is_verified VARCHAR(255) NOT NULL DEFAULT 'False',
    verification_otp INTEGER,
    auth_method VARCHAR(50) NOT NULL DEFAULT 'email',
    password VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE users ADD COLUMN name VARCHAR;
ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'student';

CREATE TABLE groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(150) NOT NULL,
    description TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE group_members (
    id SERIAL PRIMARY KEY,
    group_id UUID REFERENCES groups(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) DEFAULT 'student',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- ALTER TABLE visualizations ADD COLUMN topic VARCHAR(100);
-- ALTER TABLE visualizations ADD COLUMN detail TEXT;
CREATE TABLE visualizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    title VARCHAR(200),
    html_code TEXT,
    is_favorite BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE visualizations ADD COLUMN topic VARCHAR(100);
ALTER TABLE visualizations ADD COLUMN detail TEXT;
ALTER TABLE visualizations ADD COLUMN item VARCHAR(100);


CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    type TEXT NOT NULL,
    item_id TEXT NOT NULL,
    amount_usd DOUBLE PRECISION NOT NULL,
    status TEXT DEFAULT 'pending',
    nowpay_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_user
        FOREIGN KEY(user_id)
        REFERENCES users(id)
);


CREATE TABLE class_plans (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,    
    class_name VARCHAR(255) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    outline TEXT NOT NULL,
    total_lectures INTEGER NOT NULL,
    hours_per_lecture FLOAT NOT NULL,
    age_min INTEGER NOT NULL,
    age_max INTEGER NOT NULL,
    education_level VARCHAR(100) NOT NULL,
    books_names VARCHAR(500),
    
    -- JSONB is the optimized version of JSON for PostgreSQL
    generated_plan JSONB, 
    
    visual_id VARCHAR(255),
    visual_url TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
);

-- Index for performance when fetching a user's plans
CREATE INDEX idx_class_plans_user_id ON class_plans(user_id);

-- Enable the UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. GROUP MEMBERS TABLE
-- Links users to groups via email or user_id
CREATE TABLE group_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    group_id UUID REFERENCES groups(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    email VARCHAR NOT NULL REFERENCES users(email) ON DELETE CASCADE,
    joined_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for faster lookups
CREATE INDEX idx_group_members_group_id ON group_members(group_id);
CREATE INDEX idx_group_members_email ON group_members(email);


-- 2. GROUP MESSAGES TABLE
-- Stores chat/history within a specific group
CREATE TABLE group_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    group_id UUID REFERENCES groups(id) ON DELETE CASCADE,
    sender_id UUID REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_group_messages_group_id ON group_messages(group_id);


-- 3. GROUP SHARES TABLE
-- Stores shared class plans or visualizations
CREATE TABLE group_shares (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    group_id UUID REFERENCES groups(id) ON DELETE CASCADE,
    shared_by UUID REFERENCES users(id) ON DELETE CASCADE,
    content_type VARCHAR NOT NULL, -- e.g., 'visualization' or 'class_plan'
    content_id UUID,   -- The actual ID of the shared item
    title VARCHAR,
    url TEXT,                      -- S3 URL for visualization files
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_group_shares_group_id ON group_shares(group_id);


-- ══════════════════════════════════════════════════════════════════════════
-- NEW FEATURE TABLES (Phase 1)
-- ══════════════════════════════════════════════════════════════════════════

-- 4. QUIZZES TABLE
CREATE TABLE IF NOT EXISTS quizzes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    topic VARCHAR(255) NOT NULL,
    description TEXT,
    difficulty VARCHAR(50) DEFAULT 'medium',
    question_count INTEGER DEFAULT 0,
    source_type VARCHAR(50),
    source_id UUID,
    is_published BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_quizzes_user_id ON quizzes(user_id);

-- 5. QUIZ QUESTIONS TABLE
CREATE TABLE IF NOT EXISTS quiz_questions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    quiz_id UUID REFERENCES quizzes(id) ON DELETE CASCADE,
    question_type VARCHAR(50) NOT NULL,
    question_text TEXT NOT NULL,
    options JSONB,
    correct_answer TEXT NOT NULL,
    explanation TEXT,
    points INTEGER DEFAULT 1,
    order_index INTEGER DEFAULT 0
);

CREATE INDEX idx_quiz_questions_quiz_id ON quiz_questions(quiz_id);

-- 6. QUIZ ATTEMPTS TABLE
CREATE TABLE IF NOT EXISTS quiz_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    quiz_id UUID REFERENCES quizzes(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    answers JSONB NOT NULL,
    score DOUBLE PRECISION,
    total_points INTEGER,
    earned_points INTEGER,
    completed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_quiz_attempts_quiz_id ON quiz_attempts(quiz_id);
CREATE INDEX idx_quiz_attempts_user_id ON quiz_attempts(user_id);

-- 7. FEEDBACKS TABLE
CREATE TABLE IF NOT EXISTS feedbacks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    content_type VARCHAR(50) NOT NULL,
    content_id UUID NOT NULL,
    rating INTEGER NOT NULL,
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_feedbacks_user_id ON feedbacks(user_id);
CREATE INDEX idx_feedbacks_content ON feedbacks(content_type, content_id);

-- 8. CONTENT SUMMARIES TABLE
CREATE TABLE IF NOT EXISTS content_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    original_content TEXT NOT NULL,
    summary TEXT NOT NULL,
    summary_type VARCHAR(50) DEFAULT 'standard',
    key_points JSONB,
    word_count_original INTEGER,
    word_count_summary INTEGER,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_content_summaries_user_id ON content_summaries(user_id);

-- 9. STUDY NOTES TABLE
CREATE TABLE IF NOT EXISTS study_notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    group_id UUID REFERENCES groups(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    subject VARCHAR(100),
    tags JSONB,
    is_shared BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_study_notes_user_id ON study_notes(user_id);
CREATE INDEX idx_study_notes_group_id ON study_notes(group_id);
