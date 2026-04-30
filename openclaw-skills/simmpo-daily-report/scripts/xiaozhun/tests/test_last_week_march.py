"""
test_last_week_march.py

測試：2026 年 3 月最後一週（3/25–3/31）每天是否都能從 Looker Studio CSV 找到資料。

架構：
  - session-scoped fixture 下載 CSV 一次（需真實 browser）
  - @pytest.mark.parametrize 對 7 天各跑一個 case
  - 標記 @pytest.mark.slow，只在 pytest -m slow 時執行
"""
import os
import sys
import subprocess
import time
import pytest

sys.path.insert(0, '/Users/simmpo-claw/services')

from xiaozhun.menu_driver import open_chart_menu, select_export_data, click_export_button
from xiaozhun.download_watcher import snapshot_csvs, wait_for_new_csv
from xiaozhun.csv_parser import parse_looker_csv

URL = 'https://lookerstudio.google.com/reporting/b46242ea-190d-47b3-94d7-ff2a7119ac76/page/p_bsqvr5te1d'
DL_DIR = os.path.expanduser('~/Downloads')
AB_CMD = 'npx --prefix ~/tools/agent-browser agent-browser'

LAST_WEEK = [
    '2026-03-25',  # 週三
    '2026-03-26',  # 週四
    '2026-03-27',  # 週五
    '2026-03-28',  # 週六
    '2026-03-29',  # 週日
    '2026-03-30',  # 週一
    '2026-03-31',  # 週二
]


def make_ab_run():
    def ab_run(cmd, timeout=60):
        full = f'source ~/.zshrc && {AB_CMD} {cmd}'
        r = subprocess.run(full, shell=True, capture_output=True,
                           text=True, timeout=timeout, executable='/bin/zsh')
        return r.stdout + r.stderr
    return ab_run


@pytest.fixture(scope='session')
def march_csv_content():
    """
    下載 3 月份 CSV，回傳檔案內容字串。
    整個 session 只下載一次，7 個 parametrize case 共用。
    """
    ab_run = make_ab_run()

    ab_run(f'--profile ~/agent-browser-profile open "{URL}"')
    time.sleep(8)
    ab_run('set viewport 1600 2400')
    time.sleep(3)

    before = snapshot_csvs(DL_DIR)

    menu_snap = open_chart_menu(ab_run)
    assert menu_snap is not None, 'chart menu 打開失敗'

    ok = select_export_data(ab_run, menu_snap)
    assert ok, '找不到「匯出資料」menuitem'

    time.sleep(1)
    ok2 = click_export_button(ab_run)
    assert ok2, '找不到「匯出」button'

    csv_path = wait_for_new_csv(before, DL_DIR, timeout=30)
    assert csv_path is not None, 'CSV 下載逾時（30s）'

    ab_run('close')

    with open(csv_path, encoding='utf-8-sig') as f:
        content = f.read()

    print(f'\n[fixture] CSV 下載完成：{csv_path}')
    print(f'[fixture] 總行數：{len(content.splitlines())}')
    return content


@pytest.mark.slow
@pytest.mark.parametrize('date', LAST_WEEK)
def test_last_week_date(march_csv_content, date):
    """每天都能從 CSV 找到資料，或明確回報「找不到」（非例外）。"""
    result = parse_looker_csv(march_csv_content, date)

    print(f'\n  {date}: has_data={result["has_data"]}', end='')
    if result['has_data']:
        print(f'  花費={result["spend"]:,.0f}  購買轉換值={result["purchase_value"]:,.0f}')
    else:
        print(f'  → {result.get("error", "unknown")}')

    # 驗證：結果結構一定要正確（不管有沒有資料）
    assert 'has_data' in result
    assert 'spend' in result
    assert 'purchase_value' in result

    # 若有資料，數字要合理（> 0）
    if result['has_data']:
        assert result['spend'] > 0, f'{date} 花費不應為 0'
        assert result['purchase_value'] >= 0
