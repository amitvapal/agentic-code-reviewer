def total_price(items):
    """Sum item prices, ignoring items without a price."""
    total = 0
    for item in items:
        price = item.get("price")
        if price is not None:
            total += price
    return total
