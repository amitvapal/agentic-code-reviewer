def format_report(rows):
    """Return a comma-joined header plus one line per row."""
    header = "id,name,score"
    lines = [header]
    for row in rows:
        lines.append(f"{row['id']},{row['name']},{row['score']}")
    return "\n".join(lines)
