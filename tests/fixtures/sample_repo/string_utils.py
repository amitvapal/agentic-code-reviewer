"""Small string helpers used by the sample app."""


def reverse_string(text):
    """Return the input string reversed."""
    return text[::-1]


def is_palindrome(text):
    """Return True if text reads the same forwards and backwards."""
    cleaned = text.lower().replace(" ", "")
    return cleaned == cleaned[::-1]
