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
    class MemoryRepository:
        def __init__(self):
            self.users = {}

        def initialize(self):
            pass

        def apply_retention(self, **kwargs):
            return {"alerts": 0, "events": 0}

        def list_users(self):
            return list(self.users.values())

        def upsert_user(self, user_id, username, display_name, password_hash, role):
            self.users[username.lower()] = {
                "user_id": user_id,
                "username": username.lower(),
                "display_name": display_name,
                "password_hash": password_hash,
                "role": role,
                "created_at": "2026-09-25T00:00:00+00:00",
            }

        def get_user_by_username(self, username):
            return self.users.get(username.lower())

        def get_user_by_id(self, user_id):
            return next((user for user in self.users.values() if user["user_id"] == user_id), None)

        def list_alerts(self, **kwargs):
            return []

    repository = MemoryRepository()
    config = load_config_bundle(Path("configs"))
    app = create_app(config, repository_override=repository)
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
