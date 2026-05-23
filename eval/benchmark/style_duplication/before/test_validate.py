from validate import validate_user


def test_validate_ok():
    assert validate_user({"name": "a", "email": "b"}) is True
