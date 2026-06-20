-- Add new columns to study_rooms
ALTER TABLE study_rooms ADD COLUMN IF NOT EXISTS custom_subject VARCHAR;
ALTER TABLE study_rooms ADD COLUMN IF NOT EXISTS agenda VARCHAR;
ALTER TABLE study_rooms ADD COLUMN IF NOT EXISTS privacy VARCHAR DEFAULT 'public';
ALTER TABLE study_rooms ADD COLUMN IF NOT EXISTS invite_token VARCHAR;
ALTER TABLE study_rooms ADD COLUMN IF NOT EXISTS session_count INTEGER DEFAULT 0;
ALTER TABLE study_rooms ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;
 
-- Add new columns to study_room_participants
ALTER TABLE study_room_participants ADD COLUMN IF NOT EXISTS is_co_creator BOOLEAN DEFAULT FALSE;
 
-- Create quiz tables
CREATE TABLE IF NOT EXISTS study_room_quizzes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_id UUID REFERENCES study_rooms(id),
    creator_id UUID REFERENCES users(id),
    title VARCHAR NOT NULL,
    questions JSONB NOT NULL DEFAULT '[]',
    time_limit INTEGER DEFAULT 300,
    extended_by INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    result_shared BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
 
CREATE TABLE IF NOT EXISTS study_room_quiz_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id UUID REFERENCES study_room_quizzes(id),
    user_id UUID REFERENCES users(id),
    answers JSONB NOT NULL DEFAULT '{}',
    score INTEGER DEFAULT 0,
    submitted_at TIMESTAMP DEFAULT NOW()
);