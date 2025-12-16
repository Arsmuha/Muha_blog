"""init schema

Revision ID: 0001_init
Revises: 
Create Date: 2025-12-13

"""

from alembic import op
import sqlalchemy as sa


revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tables via SQLAlchemy (simple for homework)
    from models.db_base import Base
    from models import db_models  # noqa: F401
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)

    # SQLite FTS5 for posts
    if bind.dialect.name == "sqlite":
        op.execute(
            sa.text(
                "CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5(title, content, post_id UNINDEXED);"
            )
        )
        op.execute(
            sa.text(
                """CREATE TRIGGER IF NOT EXISTS posts_ai AFTER INSERT ON posts BEGIN
                INSERT INTO posts_fts(rowid, title, content, post_id) VALUES (new.id, new.title, new.content, new.id);
                END;"""
            )
        )
        op.execute(
            sa.text(
                """CREATE TRIGGER IF NOT EXISTS posts_ad AFTER DELETE ON posts BEGIN
                DELETE FROM posts_fts WHERE rowid = old.id;
                END;"""
            )
        )
        op.execute(
            sa.text(
                """CREATE TRIGGER IF NOT EXISTS posts_au AFTER UPDATE ON posts BEGIN
                UPDATE posts_fts SET title = new.title, content = new.content WHERE rowid = new.id;
                END;"""
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        op.execute(sa.text("DROP TABLE IF EXISTS posts_fts;"))
        op.execute(sa.text("DROP TRIGGER IF EXISTS posts_ai;"))
        op.execute(sa.text("DROP TRIGGER IF EXISTS posts_ad;"))
        op.execute(sa.text("DROP TRIGGER IF EXISTS posts_au;"))

    from models.db_base import Base
    Base.metadata.drop_all(bind=bind)
