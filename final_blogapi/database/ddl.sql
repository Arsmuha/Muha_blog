-- database/ddl.sql
-- DDL для базы данных блога

-- Таблица пользователей
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    avatar_url VARCHAR(500),
    bio TEXT,
    role VARCHAR(20) DEFAULT 'user' CHECK (role IN ('user', 'moderator', 'admin'))
);

-- Таблица категорий (тэгов)
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    color VARCHAR(7) DEFAULT '#3498db' -- цвет для отображения
);

-- Таблица постов
CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    author_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    excerpt TEXT,
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP WITH TIME ZONE,
    view_count INTEGER DEFAULT 0,

    -- Индексы для оптимизации
    CONSTRAINT fk_author FOREIGN KEY (author_id) REFERENCES users(id)
);

-- Связь постов и категорий (многие-ко-многим)
CREATE TABLE post_categories (
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (post_id, category_id)
);

-- Таблица избранного
CREATE TABLE favorites (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    saved_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,

    PRIMARY KEY (user_id, post_id),
    CONSTRAINT fk_user_fav FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT fk_post_fav FOREIGN KEY (post_id) REFERENCES posts(id)
);

-- Таблица комментариев
CREATE TABLE comments (
    id SERIAL PRIMARY KEY,
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    author_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_comment_id INTEGER REFERENCES comments(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_approved BOOLEAN DEFAULT TRUE,

    CONSTRAINT fk_post FOREIGN KEY (post_id) REFERENCES posts(id),
    CONSTRAINT fk_author FOREIGN KEY (author_id) REFERENCES users(id),
    CONSTRAINT fk_parent_comment FOREIGN KEY (parent_comment_id) REFERENCES comments(id)
);

-- Таблица подписок (пользователь на пользователя)
CREATE TABLE subscriptions (
    subscriber_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    target_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subscribed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    notifications_enabled BOOLEAN DEFAULT TRUE,

    PRIMARY KEY (subscriber_id, target_user_id),
    CONSTRAINT fk_subscriber FOREIGN KEY (subscriber_id) REFERENCES users(id),
    CONSTRAINT fk_target_user FOREIGN KEY (target_user_id) REFERENCES users(id),
    CONSTRAINT no_self_subscription CHECK (subscriber_id != target_user_id)
);

-- Таблица лайков/дизлайков (реакций)
CREATE TABLE reactions (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    reaction_type VARCHAR(10) NOT NULL CHECK (reaction_type IN ('like', 'dislike')),
    reacted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (user_id, post_id),
    CONSTRAINT fk_user_react FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT fk_post_react FOREIGN KEY (post_id) REFERENCES posts(id)
);

-- Индексы для оптимизации запросов
CREATE INDEX idx_posts_author_id ON posts(author_id);
CREATE INDEX idx_posts_status_created ON posts(status, created_at);
CREATE INDEX idx_posts_published_at ON posts(published_at);
CREATE INDEX idx_comments_post_id ON comments(post_id);
CREATE INDEX idx_comments_author_id ON comments(author_id);
CREATE INDEX idx_favorites_user_id ON favorites(user_id);
CREATE INDEX idx_favorites_post_id ON favorites(post_id);
CREATE INDEX idx_subscriptions_subscriber ON subscriptions(subscriber_id);
CREATE INDEX idx_subscriptions_target ON subscriptions(target_user_id);
CREATE INDEX idx_reactions_post_id ON reactions(post_id);
CREATE INDEX idx_reactions_user_id ON reactions(user_id);
CREATE INDEX idx_post_categories_post ON post_categories(post_id);
CREATE INDEX idx_post_categories_category ON post_categories(category_id);

-- Триггер для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_posts_updated_at BEFORE UPDATE ON posts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_comments_updated_at BEFORE UPDATE ON comments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Представление для статистики постов
CREATE VIEW post_stats AS
SELECT
    p.id,
    p.title,
    p.author_id,
    u.username as author_username,
    p.created_at,
    p.view_count,
    p.status,
    COUNT(DISTINCT c.id) as comments_count,
    COUNT(DISTINCT CASE WHEN r.reaction_type = 'like' THEN r.user_id END) as likes_count,
    COUNT(DISTINCT CASE WHEN r.reaction_type = 'dislike' THEN r.user_id END) as dislikes_count,
    COUNT(DISTINCT f.user_id) as favorites_count
FROM posts p
LEFT JOIN users u ON p.author_id = u.id
LEFT JOIN comments c ON p.id = c.post_id AND c.is_approved = TRUE
LEFT JOIN reactions r ON p.id = r.post_id
LEFT JOIN favorites f ON p.id = f.post_id
GROUP BY p.id, p.title, p.author_id, u.username, p.created_at, p.view_count, p.status;

-- Создаем тестовые данные (опционально)
INSERT INTO categories (name, slug, description) VALUES
('Программирование', 'programming', 'Статьи о программировании и разработке'),
('Дизайн', 'design', 'Статьи о дизайне и UX/UI'),
('Наука', 'science', 'Научные статьи и исследования'),
('Путешествия', 'travel', 'Рассказы о путешествиях'),
('Личное развитие', 'personal-growth', 'Советы по саморазвитию');

-- Создаем администратора по умолчанию (пароль: admin123)
INSERT INTO users (email, username, password_hash, role)
VALUES ('admin@blog.com', 'admin', 'scrypt:32768:8:1$xxxxxxxx$yyyyyyyy', 'admin');
