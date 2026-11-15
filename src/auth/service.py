"""Validación independiente de la interfaz. Solo para el prototipo local."""

import hmac
import os


def demo_mode() -> bool:
    return not (os.environ.get("ISS_USERNAME") or os.environ.get("ISS_PASSWORD"))


def authenticate(username: str, password: str) -> bool:
    if demo_mode():
        expected_user, expected_password = "astronaut", "ISS-demo-2026"
    else:
        expected_user = os.environ.get("ISS_USERNAME", "")
        expected_password = os.environ.get("ISS_PASSWORD", "")
    if not expected_user or not expected_password:
        return False
    demo_user_alias = demo_mode() and username.strip() == "astronauta"
    user_matches = demo_user_alias or hmac.compare_digest(username.strip().encode(), expected_user.encode())
    password_matches = hmac.compare_digest(password.encode(), expected_password.encode())
    return user_matches and password_matches
