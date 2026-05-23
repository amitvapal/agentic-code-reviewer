def read_text(path):
    """Read and return the contents of a file."""
    with open(path, encoding="utf-8") as handle:
        return handle.read()
