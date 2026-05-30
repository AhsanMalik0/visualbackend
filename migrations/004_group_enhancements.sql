-- Migration 004: Group enhancements - privacy, subject, feed posts with likes/comments

-- Add privacy and subject columns to groups table
ALTER TABLE groups ADD COLUMN IF NOT EXISTS privacy VARCHAR(20) DEFAULT 'private';
ALTER TABLE groups ADD COLUMN IF NOT EXISTS subject VARCHAR(150);

-- Group feed posts
CREATE TABLE IF NOT EXISTS group_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    author_id UUID NOT NULL REFERENCES users(id),
    content_type VARCHAR(50) NOT NULL,
    content_id UUID,
    text TEXT,
    title VARCHAR(500),
    is_restricted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_group_posts_group_id ON group_posts(group_id);

-- Group post likes
CREATE TABLE IF NOT EXISTS group_post_likes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES group_posts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(post_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_group_post_likes_post_id ON group_post_likes(post_id);

-- Group post comments
CREATE TABLE IF NOT EXISTS group_post_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES group_posts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    text TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_group_post_comments_post_id ON group_post_comments(post_id);
