from __future__ import annotations

from pathlib import Path

import markdown as md
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.orm import Session

from database.session import get_db
from models.db_models import Post, User, Subscription
from routers.deps import get_current_user, require_role
from services import comment_service, post_service, user_service
from services.category_service import list_categories

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="templates")


def _markdown_to_html(text_value: str) -> str:
    return md.markdown(text_value, extensions=["extra", "tables", "fenced_code"])


@router.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    q: str | None = None,
    category: str | None = None,
    page: int = 1,
    per_page: int = 10,
    feed: str | None = None,
    db: Session = Depends(get_db),
):
    user_id = getattr(request.state, "user_id", None)

    posts, total = post_service.list_posts(
        db,
        q=q,
        category_slug=category,
        page=page,
        per_page=per_page,
        feed=feed,
        viewer_id=int(user_id) if user_id else None,
    )

    items = []
    for p in posts:
        counts = post_service.get_post_counts(db, p.id)
        cats = post_service.get_post_categories(db, p.id)
        items.append(
            {
                "post": p,
                "counts": counts,
                "categories": cats,
                "author": db.get(User, p.author_id),
            }
        )

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "items": items,
            "categories": list_categories(db),
            "q": q or "",
            "category": category or "",
            "page": page,
            "per_page": per_page,
            "total": total,
            "feed": feed or "",
        },
    )


@router.get("/post/{post_id}", response_class=HTMLResponse)
def post_page(request: Request, post_id: int, db: Session = Depends(get_db)):
    post = post_service.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post_service.increment_view(db, post)
    post = post_service.get_post(db, post_id)

    counts = post_service.get_post_counts(db, post_id)
    cats = post_service.get_post_categories(db, post_id)
    author = db.get(User, post.author_id)
    comments = comment_service.list_comments(db, post_id=post_id)

    user_id = getattr(request.state, "user_id", None)
    favorited = False
    my_reaction = None
    if user_id:
        favorited = post_service.is_favorited(db, user_id=int(user_id), post_id=post_id)
        my_reaction = post_service.get_user_reaction(db, user_id=int(user_id), post_id=post_id)

    return templates.TemplateResponse(
        "post.html",
        {
            "request": request,
            "post": post,
            "post_html": _markdown_to_html(post.content),
            "counts": counts,
            "categories": cats,
            "author": author,
            "comments": comments,
            "favorited": favorited,
            "my_reaction": my_reaction,
        },
    )


@router.get("/posts/create", response_class=HTMLResponse)
def create_post_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return templates.TemplateResponse(
        "create_post.html",
        {"request": request, "categories": list_categories(db)},
    )


@router.post("/posts/create")
def create_post_action(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    status_value: str = Form("draft", alias="status"),
    category_ids: list[int] = Form([]),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    post = post_service.create_post(
        db,
        author_id=user.id,
        title=title,
        content=content,
        status=status_value,
        category_ids=category_ids,
    )
    return RedirectResponse(f"/post/{post.id}", status_code=status.HTTP_302_FOUND)


@router.get("/posts/{post_id}/edit", response_class=HTMLResponse)
def edit_post_page(
    request: Request,
    post_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    post = post_service.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if user.role not in ("admin", "moderator") and post.author_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    current_cats = {pc.category_id for pc in post.categories}
    return templates.TemplateResponse(
        "edit_post.html",
        {
            "request": request,
            "post": post,
            "categories": list_categories(db),
            "current_cats": current_cats,
        },
    )


@router.post("/posts/{post_id}/edit")
def edit_post_action(
    request: Request,
    post_id: int,
    title: str = Form(...),
    content: str = Form(...),
    status_value: str = Form("draft", alias="status"),
    category_ids: list[int] = Form([]),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    post = post_service.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if user.role not in ("admin", "moderator") and post.author_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    post_service.update_post(
        db,
        post=post,
        title=title,
        content=content,
        status=status_value,
        category_ids=category_ids,
    )
    return RedirectResponse(f"/post/{post_id}", status_code=status.HTTP_302_FOUND)


@router.post("/posts/{post_id}/delete")
def delete_post_action(
    post_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    post = post_service.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if user.role not in ("admin", "moderator") and post.author_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    post_service.delete_post(db, post)
    return RedirectResponse("/", status_code=status.HTTP_302_FOUND)


@router.get("/favorites", response_class=HTMLResponse)
def favorites_page(
    request: Request,
    page: int = 1,
    per_page: int = 10,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    offset = (page - 1) * per_page
    posts = post_service.list_favorites(db, user_id=user.id, limit=per_page, offset=offset)
    items = []
    for p in posts:
        counts = post_service.get_post_counts(db, p.id)
        cats = post_service.get_post_categories(db, p.id)
        items.append(
            {"post": p, "counts": counts, "categories": cats, "author": db.get(User, p.author_id)}
        )
    return templates.TemplateResponse(
        "favorites.html",
        {"request": request, "items": items, "page": page, "per_page": per_page},
    )


@router.get("/profile", response_class=HTMLResponse)
def profile_page(
    request: Request,
    user: User = Depends(get_current_user),
):
    return templates.TemplateResponse("profile.html", {"request": request, "user": user})


@router.post("/profile")
async def profile_update(
    request: Request,
    bio: str = Form(""),
    avatar: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    avatar_url = None
    if avatar and avatar.filename:
        uploads = Path("static/uploads") / str(user.id)
        uploads.mkdir(parents=True, exist_ok=True)
        safe_name = avatar.filename.replace("/", "_").replace("\\", "_")
        path = uploads / safe_name
        path.write_bytes(await avatar.read())
        avatar_url = "/" + str(path).replace("\\", "/")

    user_service.update_user(
        db,
        user=user,
        bio=bio,
        avatar_url=avatar_url if avatar_url else user.avatar_url,
    )
    return RedirectResponse("/profile", status_code=status.HTTP_302_FOUND)


@router.get("/users", response_class=HTMLResponse)
def users_search_page(request: Request, q: str | None = None, db: Session = Depends(get_db)):
    users = user_service.search_users(db, q=q, limit=50, offset=0) if q else []
    viewer_id = getattr(request.state, "user_id", None)
    following: set[int] = set()
    if viewer_id:
        rows = (
            db.query(Subscription.target_user_id)
            .filter(Subscription.subscriber_id == int(viewer_id))
            .all()
        )
        following = {int(r[0]) for r in rows}

    return templates.TemplateResponse(
        "users.html",
        {"request": request, "users": users, "q": q or "", "following": following},
    )


@router.post("/users/{user_id}/follow")
def follow_action(
    user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from services.subscription_service import toggle_subscription

    toggle_subscription(db, subscriber_id=user.id, target_user_id=user_id)
    return RedirectResponse(f"/users?q=", status_code=status.HTTP_302_FOUND)


@router.get("/admin", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    users_total = db.query(User).count()
    posts_total = db.query(Post).count()
    published_total = db.query(Post).filter(Post.status == "published").count()

    rows = db.execute(
        text(
            "SELECT strftime('%Y-%m', created_at) AS ym, COUNT(*) AS cnt "
            "FROM users GROUP BY ym ORDER BY ym DESC LIMIT 6"
        )
    ).fetchall()
    regs = list(reversed([{"month": r[0], "count": int(r[1])} for r in rows]))

    return templates.TemplateResponse(
        "admin_dashboard.html",
        {
            "request": request,
            "users_total": users_total,
            "posts_total": posts_total,
            "published_total": published_total,
            "regs": regs,
        },
    )
