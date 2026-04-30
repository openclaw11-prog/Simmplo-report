"""
download_watcher.py — 偵測 ~/Downloads 新增的 CSV

責任：
  只比對新增檔案 + .csv 副檔名，不依賴固定檔名。
  純 filesystem 操作，不呼叫 browser。
"""
import glob
import os
import time
from typing import Optional


def snapshot_csvs(dl_dir: str) -> frozenset[str]:
    """取得目錄下所有 .csv 的絕對路徑集合。"""
    return frozenset(glob.glob(os.path.join(dl_dir, '*.csv')))


def detect_new_csv(before: frozenset[str], after: frozenset[str]) -> Optional[str]:
    """回傳新增的那個 .csv 路徑，若有多個取最新修改時間者；無新增回傳 None。"""
    new_files = after - before
    if not new_files:
        return None
    return max(new_files, key=os.path.getmtime)


def wait_for_new_csv(
    before: frozenset[str],
    dl_dir: str,
    timeout: int = 30,
    interval: float = 1.0,
) -> Optional[str]:
    """
    輪詢等待新 .csv 出現。
    timeout 秒內未出現回傳 None。
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        time.sleep(interval)
        after = snapshot_csvs(dl_dir)
        found = detect_new_csv(before, after)
        if found:
            return found
    return None
