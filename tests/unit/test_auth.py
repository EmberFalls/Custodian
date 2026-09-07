from pathlib import Path

from fastapi.testclient import TestClient

from custodian.api.app import create_app
from custodian.api.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from custodian.config import load_config_bundle


def test_argon2_hashing():
    password = "SuperSecretPassword2026!"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_flow():
    token = create_access_token("usr_123", "testuser", "Admin")
    payload = decode_access_token(token)
    assert payload["sub"] == "usr_123"
    assert payload["username"] == "testuser"
    assert payload["role"] == "Admin"


def test_auth_api_endpoints(tmp_path: Path):
    db_path = tmp_path / "test_custodian.db"
    config = load_config_bundle(Path("configs"))
    new_storage = config.storage.model_copy(update={"database_path": db_path})
    config = config.model_copy(update={"storage": new_storage})

    app = create_app(config)
    client = TestClient(app)

    # 1. Fetch demo credentials
    demo_res = client.get("/api/v1/auth/demo-credentials")
    assert demo_res.status_code == 200
    creds = demo_res.json()
    assert len(creds) == 3

    # 2. Login with Admin credentials
    admin_cred = next(c for c in creds if c["role"] == "Admin")
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": admin_cred["username"], "password": admin_cred["password"]},
    )
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    assert token_data["user"]["role"] == "Admin"

    # 3. Access /me with Bearer token
    token = token_data["access_token"]
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["username"] == admin_cred["username"]
    
    # 4. Invalid password test
    bad_login = client.post(
        "/api/v1/auth/login",
        json={"username": admin_cred["username"], "password": "WrongPassword!"},
    )
    assert bad_login.status_code == 401
