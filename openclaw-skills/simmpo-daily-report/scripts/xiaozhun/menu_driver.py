"""
menu_driver.py — Looker Studio chart-level menu 互動

SOLID: Dependency Inversion — ab_run 由呼叫者注入。
"""
import re
import time
from typing import Callable, Optional

AbRun = Callable[[str], str]

_REF_RE = r'ref=(e\d+)'
_HOVER_Y_RANGE = range(600, 1500, 50)
_HOVER_X = 800

# 目標表格的必要特徵（都要命中才算正確圖表）
_TARGET_CHART_TITLE = '廣告成效總預覽'
_TARGET_NEARBY_CONTEXT = 5  # toolbar 前幾行要有 chart title


def _find_ref(pattern: str, snap: str) -> Optional[str]:
    for line in snap.splitlines():
        if re.search(pattern, line):
            m = re.search(_REF_RE, line)
            if m:
                return m.group(1)
    return None


def _menu_has_export(snap: str) -> bool:
    return 'menuitem' in snap and ('匯出圖表' in snap or '匯出資料' in snap)


def _toolbar_near_target_chart(snap: str) -> bool:
    """
    確認「顯示圖表選單」button 出現在「廣告成效總預覽」附近。
    策略：找到 toolbar 的行號，往前 N 行內要有 chart title。
    """
    lines = snap.splitlines()
    toolbar_idx = None
    for i, line in enumerate(lines):
        if '顯示圖表選單' in line:
            toolbar_idx = i
            break

    if toolbar_idx is None:
        return False

    # 往前 _TARGET_NEARBY_CONTEXT 行找 chart title
    start = max(0, toolbar_idx - _TARGET_NEARBY_CONTEXT)
    nearby = '\n'.join(lines[start:toolbar_idx + 1])
    return _TARGET_CHART_TITLE in nearby


def open_chart_menu(ab_run: AbRun, chart_ref: str = '') -> Optional[str]:
    """
    掃描不同 y 位置，找到「廣告成效總預覽」的 chart-level menu。

    雙重驗證：
      1. hover 後確認 toolbar 緊鄰「廣告成效總預覽」
      2. click 後確認 menu 有「匯出」選項
    """
    for y in _HOVER_Y_RANGE:
        ab_run(f'mouse move {_HOVER_X} {y}')
        time.sleep(0.4)
        snap = ab_run('snapshot -i')

        btn_ref = _find_ref('button.*顯示圖表選單', snap)
        if not btn_ref:
            continue

        # 驗證 1：toolbar 是否緊鄰目標圖表
        if not _toolbar_near_target_chart(snap):
            continue

        # 驗證通過，click
        ab_run(f'click @{btn_ref}')
        time.sleep(1.0)
        menu_snap = ab_run('snapshot -i')

        # 驗證 2：menu 有匯出選項
        if _menu_has_export(menu_snap):
            print(f'[menu_driver] y={y} 找到正確圖表 menu (btn_ref={btn_ref})')
            _log_menu(menu_snap)
            return menu_snap

        ab_run('press Escape')
        time.sleep(0.3)

    print('[menu_driver] 掃描全部 y 都找不到正確的圖表 menu')
    return None


def select_export_data(ab_run: AbRun, menu_snap: str) -> bool:
    ref = _find_ref('menuitem.*匯出資料', menu_snap)
    if ref:
        ab_run(f'click @{ref}')
        time.sleep(0.5)
        return True

    sub_ref = _find_ref('menuitem.*匯出圖表', menu_snap)
    if sub_ref:
        ab_run(f'click @{sub_ref}')
        time.sleep(0.5)
        snap2 = ab_run('snapshot -i')
        ref2 = _find_ref('menuitem.*匯出資料', snap2)
        if ref2:
            ab_run(f'click @{ref2}')
            time.sleep(0.5)
            return True

    print('[menu_driver:select_export_data] 找不到匯出資料 menuitem')
    _log_menu(menu_snap)
    return False


def click_export_button(ab_run: AbRun) -> bool:
    snap = ab_run('snapshot -i')
    ref = _find_ref('button.*"匯出"', snap)
    if not ref:
        print('[menu_driver:click_export_button] 找不到匯出 button')
        return False
    ab_run(f'click @{ref}')
    return True


def _log_menu(snap: str) -> None:
    for line in snap.splitlines():
        if any(k in line for k in ['menuitem', '匯出', '顯示圖表', '廣告成效']):
            print(f'  {line.strip()}')
