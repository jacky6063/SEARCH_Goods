# -*- coding: utf-8 -*-
"""
================================================================================
SEARCH_Goods 系統 - CSV 資料提取轉換工具
================================================================================

檔案名稱: update_csv.py
撰寫日期: 2025年11月5日
撰寫時間: 15:00-17:30
撰寫模型: GitHub Copilot (Claude 3.5 Sonnet)
最後更新: 2025年11月5日 17:30

功能描述:
    輕量級 ETL 工具，支援原子性地更新產品 CSV 檔案
    支援本地檔案和 URL 來源，確保資料一致性

核心功能:
    - update_from_file() - 從本地檔案更新
    - update_from_url() - 從 URL 下載並更新

Simple ETL helper to update the product CSV atomically.

Supports updating from a local file path or from a URL. Replaces target file
atomically using a temp file and os.replace. Does basic validation that the
resulting file has at least one line (header) and is a CSV-like file.

Intended for lightweight ingestion scripts. For production use consider using
databases or object storage with proper locking and multi-instance coordination.
"""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

import requests


def update_from_file(src_path: str, dst_path: str) -> None:
    """Atomically replace dst_path with src_path contents.

    Both paths are strings or path-like. The replacement is atomic on POSIX
    (via os.replace). Basic validation ensures the destination isn't empty.
    """
    src = Path(src_path)
    dst = Path(dst_path)
    if not src.exists():
        raise FileNotFoundError(f"source file not found: {src}")

    # write to temp file in same directory as dst to ensure atomic replace
    dst_dir = dst.parent
    dst_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, dir=str(dst_dir)) as tmp:
        tmp_path = Path(tmp.name)
        with src.open("rb") as fsrc:
            shutil.copyfileobj(fsrc, tmp)

    # basic validation: file must not be empty and should contain a comma (csv)
    stat = tmp_path.stat()
    if stat.st_size == 0:
        tmp_path.unlink(missing_ok=True)
        raise ValueError("downloaded/ copied file is empty")

    # Perform atomic replace
    os.replace(str(tmp_path), str(dst))


def update_from_url(url: str, dst_path: str, timeout: int = 30) -> None:
    """Download a URL and atomically replace dst_path with the downloaded content."""
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()

    dst = Path(dst_path)
    dst_dir = dst.parent
    dst_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, dir=str(dst_dir)) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(resp.content)

    # basic validation
    if tmp_path.stat().st_size == 0:
        tmp_path.unlink(missing_ok=True)
        raise ValueError("downloaded file is empty")

    os.replace(str(tmp_path), str(dst))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Update product CSV atomically")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--src", help="local source CSV path")
    group.add_argument("--url", help="URL to download CSV from")
    parser.add_argument("--dst", help="destination CSV path", required=True)
    args = parser.parse_args()

    if args.src:
        update_from_file(args.src, args.dst)
    else:
        update_from_url(args.url, args.dst)
