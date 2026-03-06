"""
JWT authentication service for the API layer.

How the auth flow works:
    1. User sends username + password to ``POST /auth/login``
    2. ``authenticate()`` checks credentials against the user store
    3. ``create_token()`` mints a JWT with the user's role embedded
    4. Client includes the JWT in subsequent requests as
       ``Authorization: Bearer <token>``
    5. ``decode_token()`` validates the JWT and extracts the role


Usage:
    auth = JwtAuthService(settings)
    user = auth.authenticate("admin", "admin123")
    token = auth.create_token(user["username"], user["role"])
    payload = auth.decode_token(token)
"""

import hashlib
import time
from typing import Optional

import jwt

from config.settings import Settings


class JwtAuthService:
    """Handles user authentication and JWT token lifecycle.

    Combines credential verification and token management into one service.
    The user store is in-memory for demo purposes — swap it for a database
    in production.

    Attributes:
        settings: Application configuration with JWT secret and expiry.
        USER_STORE: Demo user credentials. Each entry has a SHA-256 hashed
                    password and a role string.
    """

    USER_STORE = {
        "admin": {
            "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
            "role": "admin",
        },
        "intern": {
            "password_hash": hashlib.sha256("intern123".encode()).hexdigest(),
            "role": "intern",
        },
    }

    def __init__(self, settings: Settings):
        """Initialize with settings containing JWT configuration.

        Args:
            settings: Must include ``jwt_secret``, ``jwt_algorithm``,
                      and ``jwt_expiry_hours``.
        """
        self.settings = settings

    def authenticate(self, username: str, password: str) -> Optional[dict]:
        """Verify credentials against the user store.

        Args:
            username: The login name to look up.
            password: Plaintext password to hash and compare.

        Returns:
            A dict with ``username`` and ``role`` if credentials match,
            or None if the user doesn't exist or the password is wrong.
        """
        user = self.USER_STORE.get(username)
        if user is None:
            return None
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if password_hash != user["password_hash"]:
            return None
        return {"username": username, "role": user["role"]}

    def create_token(self, username: str, role: str) -> str:
        """Mint a JWT token with the user's identity and role.

        The token payload contains:
            - ``sub``: Username (JWT standard "subject" claim)
            - ``role``: The user's role for RBAC (custom claim)
            - ``exp``: Expiration timestamp (UTC)
            - ``iat``: Issued-at timestamp (UTC)

        Args:
            username: The authenticated user's login name.
            role: The user's role ("admin" or "intern").

        Returns:
            An encoded JWT string.
        """
        payload = {
            "sub": username,
            "role": role,
            "exp": int(time.time()) + self.settings.jwt_expiry_hours * 3600,
            "iat": int(time.time()),
        }
        return jwt.encode(
            payload, self.settings.jwt_secret, algorithm=self.settings.jwt_algorithm
        )

    def decode_token(self, token: str) -> Optional[dict]:
        """Validate and decode a JWT token.

        Checks the signature (was it signed with our secret?) and expiration
        (is it still valid?). If either check fails, returns None.

        Args:
            token: The encoded JWT string from the Authorization header.

        Returns:
            The decoded payload dict (with ``sub``, ``role``, ``exp``, ``iat``)
            if the token is valid, or None if it's expired or tampered with.
        """
        try:
            payload = jwt.decode(
                token,
                self.settings.jwt_secret,
                algorithms=[self.settings.jwt_algorithm],
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
