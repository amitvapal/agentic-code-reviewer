from classify import classify


def test_classify():
    assert classify(-1) == "negative"
    assert classify(0) == "zero"
    assert classify(5) == "positive"
