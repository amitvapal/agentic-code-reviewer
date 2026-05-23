from pricing import total_price


def test_total_price_skips_missing():
    items = [{"price": 10}, {"name": "no-price"}, {"price": 5}]
    assert total_price(items) == 15
