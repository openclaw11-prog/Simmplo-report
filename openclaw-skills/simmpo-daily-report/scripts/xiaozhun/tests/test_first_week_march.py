"""
test_first_week_march.py — 3 月第一週（3/1–3/7）
"""
import os, sys, subprocess, time, pytest
sys.path.insert(0, '/Users/simmpo-claw/services')

from xiaozhun.menu_driver import open_chart_menu, select_export_data, click_export_button
from xiaozhun.download_watcher import snapshot_csvs, wait_for_new_csv
from xiaozhun.csv_parser import parse_looker_csv

URL = 'https://lookerstudio.google.com/reporting/b46242ea-190d-47b3-94d7-ff2a7119ac76/page/p_bsqvr5te1d'
DL_DIR = os.path.expanduser('~/Downloads')
AB_CMD = 'npx --prefix ~/tools/agent-browser agent-browser'

FIRST_WEEK = [
    '2026-03-01',  # 週日
    '2026-03-02',  # 週一
    '2026-03-03',  # 週二
    '2026-03-04',  # 週三
    '2026-03-05',  # 週四
    '2026-03-06',  # 週五
    '2026-03-07',  # 週六
]

def make_ab_run():
    def ab_run(cmd, timeout=60):
        r = subprocess.run(f'source ~/.zshrc && {AB_CMD} {cmd}', shell=True,
                           capture_output=True, text=True, timeout=timeout, executable='/bin/zsh')
        return r.stdout + r.stderr
    return ab_run

@pytest.fixture(scope='session')
def march_csv_content():
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
    assert click_export_button(ab_run), '找不到「匯出」button'

    csv_path = wait_for_new_csv(before, DL_DIR, timeout=30)
    assert csv_path is not None, 'CSV 下載逾時'

    ab_run('close')

    with open(csv_path, encoding='utf-8-sig') as f:
        content = f.read()

    print(f'\n[fixture] {csv_path}  ({len(content.splitlines())} 行)')
    return content

@pytest.mark.slow
@pytest.mark.parametrize('date', FIRST_WEEK)
def test_first_week_date(march_csv_content, date):
    result = parse_looker_csv(march_csv_content, date)

    print(f'\n  {date}: has_data={result["has_data"]}', end='')
    if result['has_data']:
        print(f'  花費={result["spend"]:,.0f}  購買轉換值={result["purchase_value"]:,.0f}')
    else:
        print(f'  → {result.get("error", "unknown")}')

    assert 'has_data' in result
    assert 'spend' in result
    assert 'purchase_value' in result
    if result['has_data']:
        assert result['spend'] > 0
        assert result['purchase_value'] >= 0
