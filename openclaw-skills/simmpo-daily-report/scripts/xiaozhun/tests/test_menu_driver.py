"""
test_menu_driver.py

單元測試：用 stub ab_run 驗證邏輯（不啟動真實 browser）。
整合測試：標記 @pytest.mark.slow，需要真實 Looker Studio session，
         跑時用 pytest -m slow。
"""
import pytest
import sys
sys.path.insert(0, '/Users/simmpo-claw/services')

from xiaozhun.menu_driver import select_export_data, click_export_button, _menu_has_export


# ── snapshot fixtures ──────────────────────────────────────────────────

SNAP_WITH_EXPORT_DATA = """\
  menu [ref=e50]
    menuitem "排序依據" [ref=e51]
    menuitem "匯出資料" [ref=e55]
    menuitem "匯出圖表..." [ref=e56]
    menuitem "另存為 PNG" [ref=e57]
"""

SNAP_WITH_ONLY_EXPORT_CHART = """\
  menu [ref=e50]
    menuitem "排序依據" [ref=e51]
    menuitem "匯出圖表..." [ref=e56]
"""

SNAP_EXPORT_DIALOG = """\
  dialog "匯出資料" [ref=e70]
    textbox "名稱" [ref=e71]
    radio "CSV" checked [ref=e72]
    button "取消" [ref=e73]
    button "匯出" [ref=e74]
"""

SNAP_NO_MENU = """\
  generic "廣告成效總預覽" [ref=e30]
"""


class TestMenuVisible:
    def test_visible_when_menuitem_and_export(self):
        assert _menu_has_export(SNAP_WITH_EXPORT_DATA) is True

    def test_not_visible_without_menu(self):
        assert _menu_has_export(SNAP_NO_MENU) is False


class TestSelectExportData:
    def test_clicks_export_data_directly(self):
        clicked = []
        def stub_ab(cmd):
            clicked.append(cmd)
            return ''
        # 注入 menu snap 後直接呼叫
        result = select_export_data(stub_ab, SNAP_WITH_EXPORT_DATA)
        assert result is True
        assert any('e55' in c for c in clicked), f'expected click @e55 in {clicked}'

    def test_falls_back_to_submenu(self):
        calls = []
        def stub_ab(cmd):
            calls.append(cmd)
            if 'snapshot' in cmd:
                # 第一次 snapshot（展開子選單後）回傳有匯出資料的內容
                return SNAP_WITH_EXPORT_DATA
            return ''
        result = select_export_data(stub_ab, SNAP_WITH_ONLY_EXPORT_CHART)
        assert result is True
        assert any('e56' in c for c in calls), 'should have clicked 匯出圖表...'

    def test_returns_false_if_no_menu_items(self):
        result = select_export_data(lambda cmd: '', SNAP_NO_MENU)
        assert result is False


class TestClickExportButton:
    def test_finds_and_clicks_export(self):
        clicked = []
        def stub_ab(cmd):
            clicked.append(cmd)
            if 'snapshot' in cmd:
                return SNAP_EXPORT_DIALOG
            return ''
        result = click_export_button(stub_ab)
        assert result is True
        assert any('e74' in c for c in clicked)

    def test_returns_false_when_no_button(self):
        result = click_export_button(lambda cmd: SNAP_NO_MENU if 'snapshot' in cmd else '')
        assert result is False


# ── 整合測試（需真實 browser，標記 slow）────────────────────────────────

@pytest.mark.slow
def test_full_flow_real_browser():
    """
    完整流程測試：開啟 Looker Studio → 找圖表 → 打開 menu → 匯出 CSV。
    只在 pytest -m slow 時執行。
    需要 ~/agent-browser-profile 有效的 Google session。
    """
    import subprocess, time, os, glob

    AB_CMD = 'npx --prefix ~/tools/agent-browser agent-browser'

    def ab_run(cmd):
        full = f'source ~/.zshrc && {AB_CMD} {cmd}'
        r = subprocess.run(full, shell=True, capture_output=True, text=True,
                           timeout=60, executable='/bin/zsh')
        return r.stdout + r.stderr

    from xiaozhun.menu_driver import open_chart_menu, select_export_data, click_export_button
    from xiaozhun.download_watcher import snapshot_csvs, wait_for_new_csv
    from xiaozhun.csv_parser import parse_looker_csv

    URL = 'https://lookerstudio.google.com/reporting/b46242ea-190d-47b3-94d7-ff2a7119ac76/page/p_bsqvr5te1d'
    DL_DIR = os.path.expanduser('~/Downloads')

    ab_run(f'--profile ~/agent-browser-profile open "{URL}"')
    time.sleep(8)
    ab_run('set viewport 1600 2400')
    time.sleep(3)

    before = snapshot_csvs(DL_DIR)

    menu_snap = open_chart_menu(ab_run, chart_ref='')
    assert menu_snap is not None, 'chart menu 打開失敗'

    ok = select_export_data(ab_run, menu_snap)
    assert ok, '找不到「匯出資料」menuitem'

    time.sleep(1)
    ok2 = click_export_button(ab_run)
    assert ok2, '找不到「匯出」button'

    csv_path = wait_for_new_csv(before, DL_DIR, timeout=30)
    assert csv_path is not None, 'CSV 下載逾時'

    with open(csv_path, encoding='utf-8-sig') as f:
        content = f.read()

    result = parse_looker_csv(content, '2026-03-01')
    # 只要欄位存在即可，數字不檢查（資料隨時更新）
    assert 'has_data' in result

    ab_run('close')
