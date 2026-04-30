"""
date_utils.py — Looker Studio 日期正規化

支援格式：
  2026年3月27日  ->  2026-03-27
  2026-03-27     ->  2026-03-27
  2026/3/27      ->  2026-03-27
  3/27/2026      ->  2026-03-27
  3/27/26        ->  2026-03-27
"""
import re
from datetime import datetime


def normalize_looker_date(s: str) -> str:
    """將各種日期格式統一轉為 YYYY-MM-DD。無法解析時 raise ValueError。"""
    s = s.strip()

    # 2026年3月27日
    m = re.match(r'^(\d{4})年(\d{1,2})月(\d{1,2})日$', s)
    if m:
        return f'{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}'

    # 2026-03-27
    m = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})$', s)
    if m:
        return f'{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}'

    # 2026/3/27
    m = re.match(r'^(\d{4})/(\d{1,2})/(\d{1,2})$', s)
    if m:
        return f'{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}'

    # 3/27/2026
    m = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', s)
    if m:
        return f'{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}'

    # 3/27/26  ->  assume 2000+
    m = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{2})$', s)
    if m:
        return f'20{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}'

    raise ValueError(f'cannot parse date: {s!r}')


def date_to_looker_label(date: str) -> str:
    """YYYY-MM-DD -> Looker Studio CSV Date 欄值（2026年3月27日）。"""
    dt = datetime.strptime(date, '%Y-%m-%d')
    return f'{dt.year}年{dt.month}月{dt.day}日'
