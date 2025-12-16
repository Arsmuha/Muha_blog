from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, func, or_, text
from sqlalchemy.orm import Session

from models.db_models import Category, Favorite, Post, PostCategory, Reaction, Subscription, User
from services.search_cache import posts_search_cache


def _ensure_excerpt(content: str) -> str:
    c = content.strip()
    return (c[:200] + "…") if len(c) > 200 else c


def create_post(
    db: Session,
    *,
    author_id: int,
    title: str,
    content: str,
    status: str = "draft",
    category_ids: list[int] | None = None,
) -> Post:
    post = Post(
        author_id=author_id,
        title=title,
        content=content,
        excerpt=_ensure_excerpt(content),
        status=status,
        published_at=datetime.now(timezone.utc) if status == "published" else None,
    )
    db.add(post)
    db.flush()

    if category_ids:
        for cid in set(category_ids):
            if db.get(Category, cid):
                db.add(PostCategory(post_id=post.id, category_id=cid))

    db.commit()
    db.refresh(post)
    posts_search_cache.clear()
    return post


def update_post(
    db: Session,
    *,
    post: Post,
    title: str | None = None,
    content: str | None = None,
    status: str | None = None,
    category_ids: list[int] | None = None,
) -> Post:
    if title is not None:
        post.title = title
    if content is not None:
        post.content = content
        post.excerpt = _ensure_excerpt(content)
    if status is not None:
        post.status = status
        if status == "published" and post.published_at is None:
            post.published_at = datetime.now(timezone.utc)

    if category_ids is not None:
        # Replace categories
        db.query(PostCategory).filter(PostCategory.post_id == post.id).delete()
        for cid in set(category_ids):
            if db.get(Category, cid):
                db.add(PostCategory(post_id=post.id, category_id=cid))

    db.commit()
    db.refresh(post)
    posts_search_cache.clear()
    return post


def delete_post(db: Session, post: Post) -> None:
    db.delete(post)
    db.commit()
    posts_search_cache.clear()


def get_post(db: Session, post_id: int) -> Optional[Post]:
    return db.get(Post, post_id)


def increment_view(db: Session, post: Post) -> None:
    post.view_count += 1
    db.commit()


def set_reaction(db: Session, *, user_id: int, post_id: int, reaction_type: str) -> None:
    existing = db.get(Reaction, {"user_id": user_id, "post_id": post_id})
    if existing:
        existing.reaction_type = reaction_type
    else:
        db.add(Reaction(user_id=user_id, post_id=post_id, reaction_type=reaction_type))
    db.commit()


def remove_reaction(db: Session, *, user_id: int, post_id: int) -> None:
    existing = db.get(Reaction, {"user_id": user_id, "post_id": post_id})
    if existing:
        db.delete(existing)
        db.commit()


def toggle_favorite(db: Session, *, user_id: int, post_id: int) -> bool:
    fav = db.get(Favorite, {"user_id": user_id, "post_id": post_id})
    if fav:
        db.delete(fav)
        db.commit()
        return False
    db.add(Favorite(user_id=user_id, post_id=post_id))
    db.commit()
    return True


def list_favorites(db: Session, *, user_id: int, limit: int = 20, offset: int = 0) -> list[Post]:
    return (
        db.query(Post)
        .join(Favorite, Favorite.post_id == Post.id)
        .filter(Favorite.user_id == user_id)
        .order_by(Favorite.saved_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def list_posts(
    db: Session,
    *,
    q: str | None = None,
    author_id: int | None = None,
    category_slug: str | None = None,
    status: str | None = "published",
    page: int = 1,
    per_page: int = 10,
    feed: str | None = None,
    viewer_id: int | None = None,
) -> tuple[list[Post], int]:
    """Return (posts, total_count).

    feed:
      - None: normal listing
      - 'following': posts of followed authors (viewer_id required)
      - 'recommended': naive recommend by liked categories (viewer_id required)
    """

    page = max(1, page)
    per_page = min(max(1, per_page), 50)
    offset = (page - 1) * per_page

    query = db.query(Post)

    if status:
        query = query.filter(Post.status == status)

    if author_id:
        query = query.filter(Post.author_id == author_id)

    if category_slug:
        query = query.join(PostCategory).join(Category).filter(Category.slug == category_slug)

    if feed == "following" and viewer_id:
        query = query.join(Subscription, Subscription.target_user_id == Post.author_id).filter(
            Subscription.subscriber_id == viewer_id
        )

    if q:
        # Cache only the search ids, not full objects
        key = f"{q.strip().lower()}|{author_id}|{category_slug}|{status}|{page}|{per_page}|{feed}|{viewer_id}"
        ids = posts_search_cache.get(key)
        if ids is None:
            # Prefer FTS when on SQLite
            if db.bind and db.bind.dialect.name == "sqlite":
                rows = db.execute(
                    text(
                        """
                        SELECT post_id FROM posts_fts
                        WHERE posts_fts MATCH :q
                        ORDER BY rank
                        LIMIT :limit OFFSET :offset
                        """
                    ),
                    {"q": q, "limit": per_page, "offset": offset},
                ).fetchall()
                ids = [int(r[0]) for r in rows]
                # Count approx via simple LIKE (cheap enough for homework)
                total = (
                    db.query(func.count(Post.id))
                    .filter(Post.status == status)
                    .filter(or_(Post.title.ilike(f"%{q}%"), Post.content.ilike(f"%{q}%")))
                    .scalar()
                )
            else:
                query = query.filter(or_(Post.title.ilike(f"%{q}%"), Post.content.ilike(f"%{q}%")))
                total = query.count()
                posts = (
                    query.order_by(Post.created_at.desc()).offset(offset).limit(per_page).all()
                )
                posts_search_cache[key] = [p.id for p in posts]
                return posts, int(total)

            posts_search_cache[key] = ids
            # Fetch objects
            if not ids:
                return [], int(total or 0)
            posts = (
                db.query(Post).filter(Post.id.in_(ids)).order_by(Post.created_at.desc()).all()
            )
            return posts, int(total or len(posts))

        # cached ids
        if not ids:
            return [], 0
        posts = db.query(Post).filter(Post.id.in_(ids)).order_by(Post.created_at.desc()).all()
        return posts, len(posts)

    total = query.count()
    posts = query.order_by(Post.created_at.desc()).offset(offset).limit(per_page).all()
    return posts, int(total)


def get_post_counts(db: Session, post_id: int) -> dict[str, int]:
    likes = (
        db.query(func.count(Reaction.user_id))
        .filter(and_(Reaction.post_id == post_id, Reaction.reaction_type == "like"))
        .scalar()
    )
    dislikes = (
        db.query(func.count(Reaction.user_id))
        .filter(and_(Reaction.post_id == post_id, Reaction.reaction_type == "dislike"))
        .scalar()
    )
    favorites = db.query(func.count(Favorite.user_id)).filter(Favorite.post_id == post_id).scalar()
    return {
        "likes": int(likes or 0),
        "dislikes": int(dislikes or 0),
        "favorites": int(favorites or 0),
    }


def get_post_categories(db: Session, post_id: int) -> list[Category]:
    return (
        db.query(Category)
        .join(PostCategory, PostCategory.category_id == Category.id)
        .filter(PostCategory.post_id == post_id)
        .order_by(Category.name.asc())
        .all()
    )


def is_favorited(db: Session, *, user_id: int, post_id: int) -> bool:
    return db.get(Favorite, {"user_id": user_id, "post_id": post_id}) is not None


def get_user_reaction(db: Session, *, user_id: int, post_id: int) -> str | None:
    r = db.get(Reaction, {"user_id": user_id, "post_id": post_id})
    return r.reaction_type if r else None
