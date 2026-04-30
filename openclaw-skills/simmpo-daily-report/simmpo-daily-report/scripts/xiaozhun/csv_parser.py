"""
csv_parser.py — 解析 Looker Studio 匯出的 CSV

責任：
  1. 找目標日期那一列
  2. 取花費 / 購買 / 購買轉換值
  不知道 browser、不知道網路、不知道檔案路徑。
"""
import csv
import io
import re
from typing import Optional
from .date_utils import normalize_looker_date


# 欄名可能有的變體（Looker 版本不同偶有差異）
_SPEND_COLS   = ['花費']
_PURCHASE_COLS = ['購買']
_VALUE_COLS   = ['購買轉換值']
_DATE_COLS    = ['Date']


def _parse_number(s: str) -> float:
    """'$3,314' / '3314' / '-' / '' -> float"""
    s = (s or '').strip()
    if s in ('-', ''):
        return 0.0
    return float(re.sub(r'[^\d.]', '', s) or '0')


def _find_col(headers: list[str], candidates: list[str]) -> Optional[str]:
    for c in candidates:
        if c in headers:
            return c
    return None


def parse_looker_csv(content: str, date: str) -> dict:
    """
    content: CSV 文字內容（utf-8-sig 或 utf-8）
    date:    YYYY-MM-DD
    回傳: {spend, purchases, purchase_value, has_data, error?}
    """
    target_label = _looker_label(date)
    reader = csv.DictReader(io.StringIO(content))
    headers = reader.fieldnames or []

    date_col    = _find_col(headers, _DATE_COLS)
    spend_col   = _find_col(headers, _SPEND_COLS)
    value_col   = _find_col(headers, _VALUE_COLS)
    buy_col     = _find_col(headers, _PURCHASE_COLS)

    if not date_col:
        return _empty(f'找不到 Date 欄，實際欄位: {headers}')

    for row in reader:
        raw_date = row.get(date_col, '').strip()
        try:
            normalized = normalize_looker_date(raw_date)
        except ValueError:
            continue
        if normalized != date:
            continue
        # 找到目標列
        spend = _parse_number(row.get(spend_col, '')) if spend_col else 0.0
        pv    = _parse_number(row.get(value_col, '')) if value_col else 0.0
        buys  = int(_parse_number(row.get(buy_col, ''))) if buy_col else 0
        return {'spend': spend, 'purchases': buys,
                'purchase_value': pv, 'has_data': True}

    return _empty(f'CSV 中找不到 {date}（{target_label}）')


def _looker_label(date: str) -> str:
    from datetime import datetime
    dt = datetime.strptime(date, '%Y-%m-%d')
    return f'{dt.year}年{dt.month}月{dt.day}日'


def _empty(error: str) -> dict:
    return {'spend': 0, 'purchases': 0,
            'purchase_value': 0, 'has_data': False, 'error': error}
