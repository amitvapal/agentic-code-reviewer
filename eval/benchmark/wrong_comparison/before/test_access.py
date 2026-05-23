from access import is_adult


def test_adult_boundary():
    assert is_adult(18) is True


def test_minor():
    assert is_adult(17) is False
