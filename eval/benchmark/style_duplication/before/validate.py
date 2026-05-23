def validate_user(user):
    """Validate that a user dict has a name and an email."""
    if not user.get("name"):
        raise ValueError("name is required")
    if not user.get("email"):
        raise ValueError("email is required")
    return True
