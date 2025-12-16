from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database.session import get_db
from models.db_models import Post, User
from routers.deps import get_current_user, require_role
from schemas.comments import CommentCreate, CommentResponse
from schemas.posts import PostCreate, PostResponse, PostUpdate
from services import comment_service, post_service
from services.realtime import manager

router = APIRouter(prefix="/api/posts", tags=["posts"])


def _post_to_response(db: Session, post: Post) -> dict:
    counts = post_service.get_post_counts(db, post.id)
    cats = post_service.get_post_categories(db, post.id)
    author_username = post.author.username if post.author else None
    return {
        "id": post.id,
        "author_id": post.author_id,
        "author_username": author_username,
        "title": post.title,
        "content": post.content,
        "excerpt": post.excerpt,
        "status": post.status,
        "created_at": post.created_at,
        "updated_at": post.updated_at,
        "published_at": post.published_at,
        "view_count": post.view_count,
        "likes": counts["likes"],
        "dislikes": counts["dislikes"],
        "favorites": counts["favorites"],
        "categories": [{"id": c.id, "name": c.name, "slug": c.slug, "color": c.color} for c in cats],
    }


def _can_edit(user: User, post: Post) -> bool:
    return user.role in ("admin", "moderator") or post.author_id == user.id


@router.get("", response_model=dict)
def list_posts(
    q: str | None = Query(None),
    author_id: int | None = Query(None),
    category: str | None = Query(None, description="category slug"),
    feed: str | None = Query(None, description="following|recommended"),
    status_filter: str | None = Query("published", alias="status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    viewer_id = None
    posts, total = post_service.list_posts(
        db,
        q=q,
        author_id=author_id,
        category_slug=category,
        status=status_filter,
        page=page,
        per_page=per_page,
        feed=feed,
        viewer_id=viewer_id,
    )
    return {
        "page": page,
        "per_page": per_page,
        "total": total,
        "items": [_post_to_response(db, p) for p in posts],
    }


@router.post("", response_model=PostResponse, status_code=201)
async def create_post(payload: PostCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    post = post_service.create_post(
        db,
        author_id=user.id,
        title=payload.title,
        content=payload.content,
        status=payload.status,
        category_ids=payload.category_ids,
    )
    data = _post_to_response(db, post)
    await manager.broadcast({"type": "post_created", "post": {"id": post.id, "title": post.title, "author": user.username}})
    return data


@router.get("/{post_id}", response_model=PostResponse)
def get_post(post_id: int, db: Session = Depends(get_db)):
    post = post_service.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    post_service.increment_view(db, post)
    # refresh counts after view increment
    post = post_service.get_post(db, post_id)
    return _post_to_response(db, post)


@router.patch("/{post_id}", response_model=PostResponse)
def edit_post(
    post_id: int,
    payload: PostUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    post = post_service.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if not _can_edit(user, post):
        raise HTTPException(status_code=403, detail="Forbidden")
    post = post_service.update_post(
        db,
        post=post,
        title=payload.title,
        content=payload.content,
        status=payload.status,
        category_ids=payload.category_ids,
    )
    return _post_to_response(db, post)


@router.delete("/{post_id}")
def remove_post(post_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    post = post_service.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if not _can_edit(user, post):
        raise HTTPException(status_code=403, detail="Forbidden")
    post_service.delete_post(db, post)
    return {"ok": True}


@router.post("/{post_id}/like")
def like(post_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not post_service.get_post(db, post_id):
        raise HTTPException(status_code=404, detail="Post not found")
    post_service.set_reaction(db, user_id=user.id, post_id=post_id, reaction_type="like")
    return {"ok": True}


@router.post("/{post_id}/dislike")
def dislike(post_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not post_service.get_post(db, post_id):
        raise HTTPException(status_code=404, detail="Post not found")
    post_service.set_reaction(db, user_id=user.id, post_id=post_id, reaction_type="dislike")
    return {"ok": True}


@router.post("/{post_id}/unreact")
def unreact(post_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    post_service.remove_reaction(db, user_id=user.id, post_id=post_id)
    return {"ok": True}


@router.post("/{post_id}/favorite")
def favorite(post_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not post_service.get_post(db, post_id):
        raise HTTPException(status_code=404, detail="Post not found")
    state = post_service.toggle_favorite(db, user_id=user.id, post_id=post_id)
    return {"favorited": state}


@router.get("/favorites/me", response_model=dict)
def my_favorites(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    offset = (page - 1) * per_page
    posts = post_service.list_favorites(db, user_id=user.id, limit=per_page, offset=offset)
    return {"page": page, "per_page": per_page, "items": [_post_to_response(db, p) for p in posts]}


@router.get("/{post_id}/comments", response_model=list[CommentResponse])
def list_comments(post_id: int, db: Session = Depends(get_db)):
    if not post_service.get_post(db, post_id):
        raise HTTPException(status_code=404, detail="Post not found")
    comments = comment_service.list_comments(db, post_id=post_id)
    # add author usernames
    out = []
    for c in comments:
        out.append(
            {
                "id": c.id,
                "post_id": c.post_id,
                "author_id": c.author_id,
                "parent_comment_id": c.parent_comment_id,
                "content": c.content,
                "created_at": c.created_at,
                "author_username": c.author.username if c.author else None,
            }
        )
    return out


@router.post("/{post_id}/comments", response_model=CommentResponse, status_code=201)
async def add_comment(
    post_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not post_service.get_post(db, post_id):
        raise HTTPException(status_code=404, detail="Post not found")
    c = comment_service.add_comment(
        db,
        post_id=post_id,
        author_id=user.id,
        content=payload.content,
        parent_comment_id=payload.parent_comment_id,
    )
    await manager.broadcast({"type": "comment_created", "post_id": post_id, "author": user.username})
    return {
        "id": c.id,
        "post_id": c.post_id,
        "author_id": c.author_id,
        "parent_comment_id": c.parent_comment_id,
        "content": c.content,
        "created_at": c.created_at,
        "author_username": user.username,
    }