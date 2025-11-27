import os
from pathlib import Path
import tempfile

from etl.update_csv import update_from_file


def test_update_from_file_overwrites(tmp_path):
    # prepare source file
    src = tmp_path / "src.csv"
    src.write_text("col1,col2\n1,2\n")

    # prepare destination file with different content
    dst_dir = tmp_path / "dstdir"
    dst_dir.mkdir()
    dst = dst_dir / "VIEW_GOODS_enhanced.csv"
    dst.write_text("a,b\nx,y\n")

    # call update
    update_from_file(str(src), str(dst))

    # assert dst content equals src content
    assert dst.read_text() == src.read_text()


def test_update_from_file_missing_source(tmp_path):
    dst = tmp_path / "dest.csv"
    missing = tmp_path / "nope.csv"
    try:
        update_from_file(str(missing), str(dst))
        assert False, "expected FileNotFoundError"
    except FileNotFoundError:
        pass
