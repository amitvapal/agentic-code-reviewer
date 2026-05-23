from config_reader import read_text


def test_read_text(tmp_path):
    p = tmp_path / "data.txt"
    p.write_text("hello", encoding="utf-8")
    assert read_text(str(p)) == "hello"
