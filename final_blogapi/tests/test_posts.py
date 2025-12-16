import json


def _login(client):
    r = client.post("/login", data={"email": "admin@blog.com", "password": "admin123"}, allow_redirects=False)
    assert r.status_code == 302
    return r.cookies.get("access_token")


def test_posts_crud_like_favorite_comment(client):
    token = _login(client)
    headers = {"Cookie": f"access_token={token}"}

    # create post via API
    r = client.post(
        "/api/posts",
        headers=headers,
        json={"title": "Hello", "content": "This is **markdown** content", "status": "published", "category_ids": []},
    )
    assert r.status_code == 201, r.text
    post_id = r.json()["id"]

    # list posts
    r = client.get("/api/posts")
    assert r.status_code == 200
    assert r.json()["total"] >= 1

    # like
    r = client.post(f"/api/posts/{post_id}/like", headers=headers)
    assert r.status_code == 200

    # favorite toggle
    r = client.post(f"/api/posts/{post_id}/favorite", headers=headers)
    assert r.status_code == 200
    assert r.json()["favorited"] is True

    # comment
    r = client.post(f"/api/posts/{post_id}/comments", headers=headers, json={"content": "Nice post!"})
    assert r.status_code == 201, r.text

    # get post page (HTML) should render
    r = client.get(f"/post/{post_id}")
    assert r.status_code == 200
    assert "Hello" in r.text
