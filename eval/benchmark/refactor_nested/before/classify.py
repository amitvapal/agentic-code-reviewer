def classify(n):
    """Classify a number as negative, zero, or positive."""
    if n < 0:
        return "negative"
    if n == 0:
        return "zero"
    return "positive"
