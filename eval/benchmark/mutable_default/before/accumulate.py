def append_id(value, bucket=None):
    """Append value to bucket, creating a fresh list when none is given."""
    if bucket is None:
        bucket = []
    bucket.append(value)
    return bucket
