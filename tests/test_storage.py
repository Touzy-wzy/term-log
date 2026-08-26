import time

from termlog.storage import LineBuffer, LogWriter


def test_write_line_creates_file_with_timestamp_prefix(tmp_path):
    writer = LogWriter(tmp_path, prefix="session", max_size_mb=50)
    writer.write_line("hello world")
    writer.close()
    content = writer.current_path.read_text(encoding="utf-8")
    assert "hello world" in content
    assert content.startswith("[")


def test_write_meta_formats_key_value_pairs(tmp_path):
    writer = LogWriter(tmp_path, prefix="session", max_size_mb=50)
    writer.write_meta("session_start", project="E:/proj", shell="bash")
    writer.close()
    content = writer.current_path.read_text(encoding="utf-8")
    assert "session_start" in content
    assert "project=E:/proj" in content
    assert "shell=bash" in content


def test_rotates_when_exceeding_max_size(tmp_path):
    writer = LogWriter(tmp_path, prefix="session", max_size_mb=0)
    first_path = writer.current_path
    writer.write_line("a" * 100)
    writer.write_line("b" * 100)
    second_path = writer.current_path
    writer.close()
    assert first_path != second_path
    assert first_path.exists()
    assert second_path.exists()


def test_filenames_are_sorted_by_creation_order(tmp_path):
    writer = LogWriter(tmp_path, prefix="session", max_size_mb=50)
    writer.write_line("first")
    writer.close()
    time.sleep(0.01)
    writer2 = LogWriter(tmp_path, prefix="session", max_size_mb=50)
    writer2.write_line("second")
    writer2.close()
    files = sorted(tmp_path.glob("session_*.log"))
    assert len(files) == 2
    assert files[0].read_text(encoding="utf-8").find("first") != -1


def test_line_buffer_emits_complete_lines(tmp_path):
    writer = LogWriter(tmp_path, prefix="session", max_size_mb=50)
    buf = LineBuffer(writer)
    buf.feed(b"hello\nworld\n")
    writer.close()
    content = writer.current_path.read_text(encoding="utf-8")
    assert "hello" in content
    assert "world" in content
    assert content.count("[") == 2


def test_line_buffer_holds_partial_line_until_flush(tmp_path):
    writer = LogWriter(tmp_path, prefix="session", max_size_mb=50)
    buf = LineBuffer(writer)
    buf.feed(b"progress: 50%")
    content_before = writer.current_path.read_text(encoding="utf-8")
    assert content_before == ""
    buf.flush()
    writer.close()
    content_after = writer.current_path.read_text(encoding="utf-8")
    assert "progress: 50%" in content_after


def test_line_buffer_handles_split_across_feed_calls(tmp_path):
    writer = LogWriter(tmp_path, prefix="session", max_size_mb=50)
    buf = LineBuffer(writer)
    buf.feed(b"hel")
    buf.feed(b"lo\n")
    writer.close()
    content = writer.current_path.read_text(encoding="utf-8")
    assert "hello" in content
    assert content.count("[") == 1


def test_log_writer_accepts_explicit_initial_filename(tmp_path):
    writer = LogWriter(tmp_path, prefix="svc", max_size_mb=50, initial_filename="svc_fixed_name.log")
    assert writer.current_path == tmp_path / "svc_fixed_name.log"
    writer.write_line("hello")
    writer.close()
    assert (tmp_path / "svc_fixed_name.log").read_text(encoding="utf-8").find("hello") != -1


def test_line_buffer_replaces_invalid_utf8(tmp_path):
    writer = LogWriter(tmp_path, prefix="session", max_size_mb=50)
    buf = LineBuffer(writer)
    buf.feed(b"valid \xff\xfe bytes\n")
    writer.close()
    content = writer.current_path.read_text(encoding="utf-8")
    assert "valid" in content
    assert "bytes" in content
