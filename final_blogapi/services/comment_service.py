from __future__ import annotations

from sqlalchemy.orm import Session

from models.db_models import Comment


def add_comment(
    db: Session,
    *,
    post_id: int,
    author_id: int,
    content: str,
    parent_comment_id: int | None = None,
) -> Comment:
    c = Comment(
        post_id=post_id,
        author_id=author_id,
        content=content,
        parent_comment_id=parent_comment_id,
        is_approved=True,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def list_comments(db: Session, *, post_id: int) -> list[Comment]:
    return (
        db.query(Comment)
        .filter(Comment.post_id == post_id, Comment.is_approved == True)  # noqa: E712
        .order_by(Comment.created_at.asc())
        .all()
    )
