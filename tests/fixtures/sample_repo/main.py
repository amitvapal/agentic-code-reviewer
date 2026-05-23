"""Entry point that wires the sample helpers together."""

from math_utils import fibonacci
from string_utils import reverse_string


def run():
    print(fibonacci(10))
    print(reverse_string("hello"))


if __name__ == "__main__":
    run()
