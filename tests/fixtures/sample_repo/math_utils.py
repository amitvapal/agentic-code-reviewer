"""Small numeric helpers used by the sample app."""


def fibonacci(n):
    """Return the nth Fibonacci number, computed iteratively."""
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def factorial(n):
    """Return n! computed iteratively."""
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result
