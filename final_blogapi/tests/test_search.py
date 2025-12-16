def test_search_fts(client):
    # Login as admin
    r = client.post("/login", data={"email": "admin@blog.com", "password": "admin123"}, allow_redirects=False)
    token = r.cookies.get("access_token")
    headers = {"Cookie": f"access_token={token}"}

    # Create
    r = client.post(
        "/api/posts",
        headers=headers,
        json={"title": "FTS title", "content": "alpha beta gamma", "status": "published", "category_ids": []},
    )
    assert r.status_code == 201

    # Search via index page
    r = client.get("/?q=alpha")
    assert r.status_code == 200
    assert "FTS title" in r.text
