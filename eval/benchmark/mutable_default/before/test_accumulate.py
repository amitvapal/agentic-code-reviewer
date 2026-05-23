from accumulate import append_id


def test_append_id_isolated():
    assert append_id(1) == [1]
    assert append_id(2) == [2]
