from report import format_report


def test_format_report():
    rows = [{"id": 1, "name": "a", "score": 9}]
    assert format_report(rows) == "id,name,score\n1,a,9"
