"""Validation helpers for usernames and password policies."""

from __future__ import annotations

import re
from typing import List

from app.models.system_preferences import SystemPreferences

_USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]+$")


def validate_username(username: str) -> str | None:
    """Validate a username against basic formatting rules.

    Returns an error string when invalid; otherwise None.
    """
    candidate = username.strip()
    if len(candidate) < 3 or len(candidate) > 32:
        return "Username must be between 3 and 32 characters long."
    if candidate.lower() == "admin":
        return "Username 'admin' is reserved."
    if not _USERNAME_PATTERN.fullmatch(candidate):
        return "Usernames may contain letters, numbers, dots, underscores, and hyphens only."
    return None


def validate_password_policy(password: str, prefs: SystemPreferences) -> List[str]:
    """Validate a password against the configured system policy.

    Returns a list of human-readable error messages; empty list when valid.
    """
    errors: list[str] = []
    min_length = prefs.password_min_length or 12
    if len(password) < min_length:
        errors.append(f"Password must be at least {min_length} characters long.")

    if getattr(prefs, "password_require_uppercase", False) and not re.search(r"[A-Z]", password):
        errors.append("Password must include at least one uppercase letter.")

    if getattr(prefs, "password_require_lowercase", False) and not re.search(r"[a-z]", password):
        errors.append("Password must include at least one lowercase letter.")

    if getattr(prefs, "password_require_number", False) and not re.search(r"[0-9]", password):
        errors.append("Password must include at least one number.")

    if getattr(prefs, "password_require_special", False) and not re.search(
        r"[^A-Za-z0-9]", password
    ):
        errors.append("Password must include at least one special character.")

    return errors
