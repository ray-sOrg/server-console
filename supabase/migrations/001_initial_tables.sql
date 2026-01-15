-- ========================================
-- Supabase Database Schema for server-console
-- ========================================
-- 在 Supabase SQL Editor 中执行此脚本
-- ========================================

-- 1. 用户表
CREATE TABLE IF NOT EXISTS user (
    id SERIAL PRIMARY KEY,
    uid VARCHAR(36) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL, -- 'super_admin', 'admin', 'user'
    create_time TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. 婚礼照片墙表
CREATE TABLE IF NOT EXISTS wedding_photo_wall (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    src VARCHAR(255) NOT NULL,
    order_num INTEGER,
    is_show BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- 3. 婚礼音乐表
CREATE TABLE IF NOT EXISTS wedding_music (
    id SERIAL PRIMARY KEY,
    title VARCHAR(100),
    artist VARCHAR(100) NOT NULL,
    album VARCHAR(100),
    path VARCHAR(200) UNIQUE NOT NULL
);

-- 4. 图片表
CREATE TABLE IF NOT EXISTS image (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE,
    path VARCHAR(200),
    upload_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_modified TIMESTAMP WITH TIME ZONE,
    size INTEGER,
    content_type VARCHAR(100)
);

-- ========================================
-- 索引
-- ========================================

-- user 表索引
CREATE INDEX IF NOT EXISTS idx_user_uid ON user(uid);
CREATE INDEX IF NOT EXISTS idx_user_username ON user(username);

-- wedding_photo_wall 表索引
CREATE INDEX IF NOT EXISTS idx_wedding_photo_wall_order ON wedding_photo_wall(order_num);
CREATE INDEX IF NOT EXISTS idx_wedding_photo_wall_is_show ON wedding_photo_wall(is_show);

-- wedding_music 表索引
CREATE INDEX IF NOT EXISTS idx_wedding_music_path ON wedding_music(path);

-- image 表索引
CREATE INDEX IF NOT EXISTS idx_image_name ON image(name);

-- ========================================
-- 更新时间自动更新触发器
-- ========================================

-- wedding_photo_wall updated_at 自动更新
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_wedding_photo_wall_updated_at
    BEFORE UPDATE ON wedding_photo_wall
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ========================================
-- 初始化数据（可选）
-- ========================================

-- 创建默认管理员用户（密码需要使用 bcrypt/hash 生成）
-- 密码: admin123 (示例，请替换为实际 hash)
INSERT INTO user (uid, username, password, role)
VALUES (
    gen_random_uuid()::text,
    'admin',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzpLaEmc0i',
    'super_admin'
) ON CONFLICT (username) DO NOTHING;

-- ========================================
-- Row Level Security (RLS) - 可选
-- ========================================

-- 如果需要启用 RLS，取消以下注释
-- ALTER TABLE user ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE wedding_photo_wall ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE wedding_music ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE image ENABLE ROW LEVEL SECURITY;
