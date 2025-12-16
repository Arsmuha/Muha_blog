from __future__ import annotations

from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session

from .session import engine
from models.db_base import Base
from models.db_models import Category, User
from services.auth_service import get_password_hash


DEFAULT_CATEGORIES = [
    ("Программирование", "programming", "Статьи о программировании и разработке", "#3498db"),
    ("Дизайн", "design", "Статьи о дизайне и UX/UI", "#9b59b6"),
    ("Наука", "science", "Научные статьи и исследования", "#2ecc71"),
    ("Путешествия", "travel", "Рассказы о путешествиях", "#e67e22"),
    ("Личное развитие", "personal-growth", "Советы по саморазвитию", "#e74c3c"),
]


def _create_sqlite_fts(db: Session) -> None:
    """Create SQLite FTS5 table + triggers for full-text search."""
    # FTS5 is usually available in standard SQLite builds.
    # We'll keep it robust: ignore if already exists.
    db.execute(
        text(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts
            USING fts5(title, content, post_id UNINDEXED);
            """
        )
    )

    # Triggers keep FTS in sync
    db.execute(
        text(
            """
            CREATE TRIGGER IF NOT EXISTS posts_ai AFTER INSERT ON posts BEGIN
              INSERT INTO posts_fts(rowid, title, content, post_id)
              VALUES (new.id, new.title, new.content, new.id);
            END;
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TRIGGER IF NOT EXISTS posts_ad AFTER DELETE ON posts BEGIN
              DELETE FROM posts_fts WHERE rowid = old.id;
            END;
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TRIGGER IF NOT EXISTS posts_au AFTER UPDATE ON posts BEGIN
              UPDATE posts_fts SET title = new.title, content = new.content WHERE rowid = new.id;
            END;
            """
        )
    )

    # Backfill FTS if empty
    db.execute(
        text(
            """
            INSERT INTO posts_fts(rowid, title, content, post_id)
            SELECT id, title, content, id FROM posts
            WHERE id NOT IN (SELECT post_id FROM posts_fts);
            """
        )
    )


def init_db() -> None:
    Base.metadata.create_all(bind=engine)

    from database.session import SessionLocal

    db = SessionLocal()
    try:
        # FTS
        if engine.url.get_backend_name() == "sqlite":
            _create_sqlite_fts(db)

        # Seed categories
        if db.query(Category).count() == 0:
            for name, slug, desc, color in DEFAULT_CATEGORIES:
                db.add(Category(name=name, slug=slug, description=desc, color=color))

        # Seed admin user
        if db.query(User).filter(User.email == "admin@blog.com").first() is None:
            admin = User(
                email="admin@blog.com",
                username="admin",
                password_hash=get_password_hash("admin123"),
                role="admin",
                is_active=True,
                bio="Администратор по умолчанию (пароль: admin123)",
            )
            db.add(admin)

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    print("✅ DB initialized")
