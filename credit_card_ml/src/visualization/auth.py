"""
Admin Authentication Module
Single admin user authentication via environment variables.
"""

import os
from werkzeug.security import check_password_hash, generate_password_hash

ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH', '')


def get_admin_username():
    """Get admin username from environment."""
    return ADMIN_USER


def set_admin_password_hash(password_hash):
    """Set admin password hash (for initial setup)."""
    os.environ['ADMIN_PASSWORD_HASH'] = password_hash


def verify_admin_password(username, password):
    """
    Verify admin credentials.
    Returns True if credentials are valid, False otherwise.
    """
    if not username or not password:
        return False

    if username != ADMIN_USER:
        return False

    stored_hash = ADMIN_PASSWORD_HASH
    if not stored_hash:
        return False

    return check_password_hash(stored_hash, password)


def hash_password(password):
    """Generate password hash for storage."""
    return generate_password_hash(password)
