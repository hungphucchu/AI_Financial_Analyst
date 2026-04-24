"""Tests for JWT authentication flow."""

import pytest
from config.settings import Settings
from api.jwt_auth_service import JwtAuthService


@pytest.fixture
def settings():
    return Settings(
        qwen_api_key="test-key",
        jwt_secret="test-secret-key",
        jwt_algorithm="HS256",
        jwt_expiry_hours=1,
    )


@pytest.fixture
def auth(settings):
    return JwtAuthService(settings)


class TestAuthentication:

    def test_valid_admin_credentials(self, auth):
        user = auth.authenticate("admin", "admin123")
        assert user is not None
        assert user["role"] == "admin"
        assert user["username"] == "admin"

    def test_valid_intern_credentials(self, auth):
        user = auth.authenticate("intern", "intern123")
        assert user is not None
        assert user["role"] == "intern"

    def test_wrong_password_rejected(self, auth):
        assert auth.authenticate("admin", "wrongpassword") is None

    def test_unknown_user_rejected(self, auth):
        assert auth.authenticate("hacker", "password") is None


class TestJWT:

    def test_create_and_decode_token(self, auth):
        token = auth.create_token("admin", "admin")
        payload = auth.decode_token(token)

        assert payload is not None
        assert payload["sub"] == "admin"
        assert payload["role"] == "admin"

    def test_expired_token_rejected(self, settings):
        settings.jwt_expiry_hours = 0
        auth = JwtAuthService(settings)
        token = auth.create_token("admin", "admin")
        payload = auth.decode_token(token)
        assert payload is None

    def test_tampered_token_rejected(self, auth):
        token = auth.create_token("admin", "admin")
        tampered = token + "x"
        payload = auth.decode_token(tampered)
        assert payload is None

    def test_wrong_secret_rejected(self, auth):
        token = auth.create_token("admin", "admin")
        wrong_settings = Settings(
            qwen_api_key="test",
            jwt_secret="wrong-secret",
        )
        wrong_auth = JwtAuthService(wrong_settings)
        payload = wrong_auth.decode_token(token)
        assert payload is None
