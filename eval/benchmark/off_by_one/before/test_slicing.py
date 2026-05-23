from slicing import first_n


def test_first_n():
    assert first_n([1, 2, 3, 4, 5], 3) == [1, 2, 3]


def test_first_n_all():
    assert first_n([1, 2], 2) == [1, 2]
