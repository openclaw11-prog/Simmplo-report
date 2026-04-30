"""
date_range_picker.py — Looker Studio 日期範圍選擇器

SOLID:
- Single Responsibility: parse_calendar_panes 只解析 snapshot；
  DateRangePicker 只負責操作 UI
- Dependency Inversion: ab_run 與 sleep_fn 由呼叫者注入
"""
import re
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

AbRun = Callable[[str], str]

_DAY_BTN_RE = re.compile(r'button "(\d{4})年(\d{1,2})月(\d+)日" \[ref=(e\d+)\]')
_PREV_RE = re.compile(r'button "Previous month" \[ref=(e\d+)\]')
_NEXT_RE = re.compile(r'button "Next month" \[ref=(e\d+)\]')
_APPLY_RE = re.compile(r'button "套用" (\[.*?\])')


@dataclass
class CalendarPane:
    """Looker Studio 日期選擇器中的單一 calendar pane。"""
    pane_idx: int          # 0 = 左/start，1 = 右/end
    year: int
    month: int
    day_refs: Dict[int, str]   # {day: ref}
    prev_ref: Optional[str]    # Previous month button ref
    next_ref: Optional[str]    # Next month button ref


def parse_calendar_panes(snap: str) -> List[CalendarPane]:
    """
    從 snapshot 字串解析出所有 CalendarPane。

    策略：以 (Prev, Next) nav 按鈕對作為 pane 邊界。
    每個 nav pair 後面緊接著的 day buttons 屬於該 pane。
    
    可正確處理：
    - 兩個 pane 顯示不同月份
    - 兩個 pane 顯示同一月份（day refs 不同）
    - 單一 pane
    """
    lines = snap.splitlines()
    n = len(lines)

    # 找出所有 (Prev month, Next month) 的位置與 refs
    nav_sections = []  # {'prev_ref', 'next_ref', 'after_line'}
    i = 0
    while i < n:
        pm = _PREV_RE.search(lines[i])
        if pm:
            prev_ref = pm.group(1)
            next_ref = None
            after = i + 1
            for j in range(i + 1, min(i + 4, n)):
                nm = _NEXT_RE.search(lines[j])
                if nm:
                    next_ref = nm.group(1)
                    after = j + 1
                    i = j
                    break
            nav_sections.append({'prev_ref': prev_ref, 'next_ref': next_ref, 'after': after})
        i += 1

    if not nav_sections:
        return []

    # 每個 nav section 的 day buttons 範圍：[after, next_section.after - 1)
    panes = []
    for idx, nav in enumerate(nav_sections):
        start = nav['after']
        end = nav_sections[idx + 1]['after'] - 1 if idx + 1 < len(nav_sections) else n

        days: Dict[int, str] = {}
        current_ym = None
        for j in range(start, end):
            dm = _DAY_BTN_RE.search(lines[j])
            if dm:
                y, m, d, ref = int(dm.group(1)), int(dm.group(2)), int(dm.group(3)), dm.group(4)
                if current_ym is None:
                    current_ym = (y, m)
                days[d] = ref

        if current_ym:
            panes.append(CalendarPane(
                pane_idx=idx,
                year=current_ym[0],
                month=current_ym[1],
                day_refs=days,
                prev_ref=nav['prev_ref'],
                next_ref=nav['next_ref'],
            ))

    return panes


def find_apply_ref(snap: str) -> Optional[str]:
    """回傳 enabled 狀態的套用按鈕 ref；disabled 或不存在回傳 None。"""
    for line in snap.splitlines():
        m = _APPLY_RE.search(line)
        if m and 'disabled' not in m.group(1):
            ref_m = re.search(r'ref=(e\d+)', m.group(1))
            if ref_m:
                return ref_m.group(1)
    return None


def is_apply_disabled(snap: str) -> bool:
    """套用按鈕存在且為 disabled 時回傳 True。"""
    for line in snap.splitlines():
        if _APPLY_RE.search(line) and 'disabled' in line:
            return True
    return False


class DateRangePicker:
    """
    操作 Looker Studio 雙 pane 日期範圍選擇器。

    SOLID DI: ab_run 與 sleep_fn 由外部注入，便於測試。
    """

    def __init__(self, ab_run: AbRun, sleep_fn=time.sleep):
        self._ab = ab_run
        self._sleep = sleep_fn

    def select_month_range(self, year: int, month: int) -> bool:
        """
        將日期範圍設定為 year/month 的 1 日到最後一日。
        回傳 True 表示成功套用，False 表示失敗。
        """
        import calendar
        last_day = calendar.monthrange(year, month)[1]
        target = (year, month)

        # 1. 導航左 pane（start date）到目標月份
        if not self._nav_pane_to(pane_idx=0, target=target):
            return False

        # 2. 點左 pane 的第 1 日
        snap = self._ab('snapshot -i')
        panes = parse_calendar_panes(snap)
        left = self._get_pane(panes, 0)
        if left is None or 1 not in left.day_refs:
            return False
        self._ab(f'click {left.day_refs[1]}')
        self._sleep(0.5)

        # 3. 導航右 pane（end date）到目標月份
        if not self._nav_pane_to(pane_idx=1, target=target):
            return False

        # 4. 點右 pane 的最後一日
        snap2 = self._ab('snapshot -i')
        panes2 = parse_calendar_panes(snap2)
        right = self._get_pane(panes2, 1)
        if right is None or last_day not in right.day_refs:
            return False
        self._ab(f'click {right.day_refs[last_day]}')
        self._sleep(0.5)

        # 5. 等待並點套用
        return self._apply()

    # ── private ────────────────────────────────────────────────────────────────

    def _nav_pane_to(self, pane_idx: int, target: tuple, max_steps: int = 24) -> bool:
        """導航指定 pane 到目標 (year, month)。"""
        for _ in range(max_steps):
            snap = self._ab('snapshot -i')
            panes = parse_calendar_panes(snap)
            pane = self._get_pane(panes, pane_idx)
            if pane is None:
                return False
            cur = (pane.year, pane.month)
            if cur == target:
                return True
            if cur < target:
                if not pane.next_ref:
                    return False
                self._ab(f'click {pane.next_ref}')
            else:
                if not pane.prev_ref:
                    return False
                self._ab(f'click {pane.prev_ref}')
            self._sleep(0.8)
        return False

    def _apply(self, max_attempts: int = 4) -> bool:
        """點套用按鈕；若暫時 disabled 最多重試 max_attempts 次。"""
        for _ in range(max_attempts):
            snap = self._ab('snapshot -i')
            ref = find_apply_ref(snap)
            if ref:
                self._ab(f'click {ref}')
                self._sleep(4.0)
                return True
            if not is_apply_disabled(snap):
                return False  # 按鈕消失，不是 disabled
            self._sleep(0.5)
        return False

    @staticmethod
    def _get_pane(panes: List[CalendarPane], idx: int) -> Optional[CalendarPane]:
        """取 pane_idx == idx 的 pane；不存在時取最後一個（單 pane 情況）。"""
        for p in panes:
            if p.pane_idx == idx:
                return p
        return panes[-1] if panes else None
