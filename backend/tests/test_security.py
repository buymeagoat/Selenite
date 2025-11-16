"""Tests for security utilities (password hashing and JWT tokens)."""

from datetime import datetime, timedelta
from jose import jwt

from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)
from app.config import settings


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password(self):
        """Test that password is hashed correctly."""
        password = "mysecurepassword123"
        hashed = hash_password(password)

        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt hash prefix
        assert len(hashed) == 60  # bcrypt hash length

    def test_hash_password_different_hashes(self):
        """Test that same password produces different hashes (salt)."""
        password = "samepassword"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2

    def test_verify_password_correct(self):
        """Test that correct password verification returns True."""
        password = "correctpassword"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test that incorrect password verification returns False."""
        password = "correctpassword"
        wrong_password = "wrongpassword"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_empty(self):
        """Test that empty password verification returns False."""
        password = "password"
        hashed = hash_password(password)

        assert verify_password("", hashed) is False


class TestJWTTokens:
    """Test JWT token creation and validation."""

    def test_create_access_token(self):
        """Test that access token is created correctly."""
        data = {"sub": "testuser"}
        token = create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 0

        # Decode and verify payload
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        assert payload["sub"] == "testuser"
        assert "exp" in payload

    def test_create_access_token_with_expiry(self):
        """Test that token expires at specified time."""
        data = {"sub": "testuser"}
        expires_delta = timedelta(minutes=15)
        token = create_access_token(data, expires_delta=expires_delta)

        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

        # Verify expiration is approximately 15 minutes from now
        exp_timestamp = payload["exp"]
        exp_datetime = datetime.utcfromtimestamp(exp_timestamp)
        expected_exp = datetime.utcnow() + expires_delta

        # Allow 5 second tolerance
        assert abs((exp_datetime - expected_exp).total_seconds()) < 5

    def test_create_access_token_default_expiry(self):
        """Test that token uses default expiry if not specified."""
        data = {"sub": "testuser"}
        token = create_access_token(data)

        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

        exp_timestamp = payload["exp"]
        exp_datetime = datetime.utcfromtimestamp(exp_timestamp)
        expected_exp = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)

        # Allow 5 second tolerance
        assert abs((exp_datetime - expected_exp).total_seconds()) < 5

    def test_decode_access_token_valid(self):
        """Test that valid token is decoded correctly."""
        data = {"sub": "testuser", "user_id": 1}
        token = create_access_token(data)

        decoded = decode_access_token(token)

        assert decoded is not None
        assert decoded["sub"] == "testuser"
        assert decoded["user_id"] == 1

    def test_decode_access_token_invalid(self):
        """Test that invalid token returns None."""
        invalid_token = "invalid.token.here"

        decoded = decode_access_token(invalid_token)

        assert decoded is None

    def test_decode_access_token_expired(self):
        """Test that expired token returns None."""
        data = {"sub": "testuser"}
        # Create token that expires immediately
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))

        decoded = decode_access_token(token)

        assert decoded is None

    def test_decode_access_token_wrong_secret(self):
        """Test that token with wrong secret returns None."""
        data = {"sub": "testuser"}
        # Create token with different secret
        token = jwt.encode(data, "wrong-secret", algorithm=settings.algorithm)

        decoded = decode_access_token(token)

        assert decoded is None
