def test_register_and_login_flow(client):
    # Register
    r = client.post(
        "/register",
        data={
            "email": "u1@example.com",
            "username": "u1",
            "password": "secret123",
            "confirm_password": "secret123",
        },
        allow_redirects=False,
    )
    assert r.status_code == 302
    assert "access_token" in r.cookies

    # Logout
    r = client.get("/logout", allow_redirects=False)
    assert r.status_code == 302

    # Login
    r = client.post("/login", data={"email": "u1@example.com", "password": "secret123"}, allow_redirects=False)
    assert r.status_code == 302
    assert "access_token" in r.cookies
