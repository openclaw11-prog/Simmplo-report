"""
test_date_range_picker.py — TDD for DateRangePicker

測試策略：
- parse_calendar_panes: 純函式，直接用 snapshot 字串測
- find_apply_ref / is_apply_disabled: 純函式
- DateRangePicker: stub ab_run (list of canned responses), sleep_fn=no-op
"""
import pytest
from xiaozhun.date_range_picker import (
    CalendarPane,
    parse_calendar_panes,
    find_apply_ref,
    is_apply_disabled,
    DateRangePicker,
)

# ── Snapshot fixtures ─────────────────────────────────────────────────────────

def _make_pane_lines(year, month, prev_ref, next_ref, day_start_ref_num):
    """產生一個 calendar pane 的 snapshot 行。"""
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    lines = [
        f'  - button "Choose month and year" [ref=eX]',
        f'  - button "Previous month" [ref={prev_ref}]',
        f'  - button "Next month" [ref={next_ref}]',
    ]
    for d in range(1, last_day + 1):
        lines.append(f'  - button "{year}年{month}月{d}日" [ref=e{day_start_ref_num + d - 1}]')
    return lines


def _snap_two_panes(left_ym, right_ym, apply_disabled=False):
    """兩個 pane 的完整 snapshot。"""
    lines = ['  - button "getDateText()" [ref=e189]']
    lines += _make_pane_lines(*left_ym,  prev_ref='e3', next_ref='e4', day_start_ref_num=100)
    lines += _make_pane_lines(*right_ym, prev_ref='e6', next_ref='e7', day_start_ref_num=200)
    disabled = ', disabled' if apply_disabled else ''
    lines += [
        '  - button "取消" [ref=e8]',
        f'  - button "套用" [{disabled}ref=e9]' if not apply_disabled
        else '  - button "套用" [disabled, ref=e9]',
    ]
    return '\n'.join(lines)


def _snap_one_pane(ym, apply_disabled=False):
    lines = ['  - button "getDateText()" [ref=e189]']
    lines += _make_pane_lines(*ym, prev_ref='e3', next_ref='e4', day_start_ref_num=100)
    disabled_str = '[disabled, ref=e9]' if apply_disabled else '[ref=e9]'
    lines += [f'  - button "套用" {disabled_str}']
    return '\n'.join(lines)


# ── parse_calendar_panes ──────────────────────────────────────────────────────

class TestParseCalendarPanes:
    def test_two_panes_different_months(self):
        snap = _snap_two_panes((2026, 3), (2026, 4))
        panes = parse_calendar_panes(snap)
        assert len(panes) == 2
        assert panes[0].year == 2026 and panes[0].month == 3
        assert panes[1].year == 2026 and panes[1].month == 4

    def test_two_panes_correct_nav_refs(self):
        snap = _snap_two_panes((2026, 3), (2026, 4))
        panes = parse_calendar_panes(snap)
        assert panes[0].prev_ref == 'e3'
        assert panes[0].next_ref == 'e4'
        assert panes[1].prev_ref == 'e6'
        assert panes[1].next_ref == 'e7'

    def test_two_panes_correct_day_refs(self):
        snap = _snap_two_panes((2026, 3), (2026, 4))
        panes = parse_calendar_panes(snap)
        # Left pane: March has 31 days, starting at e100
        assert panes[0].day_refs[1] == 'e100'
        assert panes[0].day_refs[31] == 'e130'
        # Right pane: April has 30 days, starting at e200
        assert panes[1].day_refs[1] == 'e200'
        assert panes[1].day_refs[30] == 'e229'

    def test_two_panes_same_month(self):
        """關鍵邊界：兩個 pane 顯示同一個月份時，day refs 必須分別對應。"""
        snap = _snap_two_panes((2026, 4), (2026, 4))
        panes = parse_calendar_panes(snap)
        assert len(panes) == 2
        assert panes[0].month == 4
        assert panes[1].month == 4
        # 左 pane day 1 = e100, 右 pane day 1 = e200（不同 ref）
        assert panes[0].day_refs[1] == 'e100'
        assert panes[1].day_refs[1] == 'e200'

    def test_single_pane(self):
        snap = _snap_one_pane((2026, 4))
        panes = parse_calendar_panes(snap)
        assert len(panes) == 1
        assert panes[0].month == 4
        assert panes[0].pane_idx == 0

    def test_empty_snapshot(self):
        panes = parse_calendar_panes('  - button "getDateText()" [ref=e1]')
        assert panes == []

    def test_pane_idx_assigned_correctly(self):
        snap = _snap_two_panes((2026, 2), (2026, 3))
        panes = parse_calendar_panes(snap)
        assert panes[0].pane_idx == 0
        assert panes[1].pane_idx == 1


# ── find_apply_ref / is_apply_disabled ───────────────────────────────────────

class TestApplyButton:
    def test_find_apply_enabled(self):
        snap = '  - button "套用" [ref=e9]'
        assert find_apply_ref(snap) == 'e9'

    def test_find_apply_disabled_returns_none(self):
        snap = '  - button "套用" [disabled, ref=e9]'
        assert find_apply_ref(snap) is None

    def test_find_apply_not_present(self):
        snap = '  - button "取消" [ref=e8]'
        assert find_apply_ref(snap) is None

    def test_is_apply_disabled_true(self):
        snap = '  - button "套用" [disabled, ref=e9]'
        assert is_apply_disabled(snap) is True

    def test_is_apply_disabled_false_when_enabled(self):
        snap = '  - button "套用" [ref=e9]'
        assert is_apply_disabled(snap) is False

    def test_is_apply_disabled_false_when_absent(self):
        assert is_apply_disabled('no buttons here') is False


# ── DateRangePicker ───────────────────────────────────────────────────────────

class StubAbRun:
    """只有 snapshot -i 消耗 response；click / press 回傳空字串。"""
    def __init__(self, snap_responses: list):
        self._snaps = iter(snap_responses)
        self.calls = []

    def __call__(self, cmd: str) -> str:
        self.calls.append(cmd)
        if cmd == "snapshot -i":
            return next(self._snaps, "")
        return ""


class TestDateRangePicker:
    def _noop_sleep(self, _):
        pass

    def test_happy_path_both_panes_already_at_target(self):
        """左右 pane 都已經是目標月份，直接點 1 日和最後一日套用。"""
        snap_both_april = _snap_two_panes((2026, 4), (2026, 4))
        snap_apply_enabled = _snap_two_panes((2026, 4), (2026, 4), apply_disabled=False)

        stub = StubAbRun([
            snap_both_april,   # _nav_pane_to(0): 左已是 4 月，不需導航
            snap_both_april,   # 取 left pane day 1 ref
            snap_both_april,   # _nav_pane_to(1): 右已是 4 月，不需導航
            snap_both_april,   # 取 right pane last day ref
            snap_apply_enabled, # _apply: 套用 enabled
        ])
        picker = DateRangePicker(stub, sleep_fn=self._noop_sleep)
        result = picker.select_month_range(2026, 4)

        assert result is True
        clicks = [c for c in stub.calls if c.startswith('click')]
        assert 'click e100' in clicks   # day 1 左 pane
        assert 'click e229' in clicks   # day 30 右 pane
        assert 'click e9' in clicks     # 套用

    def test_left_pane_needs_navigation_forward(self):
        """左 pane 在 3 月，需要點 Next 前進到 4 月。"""
        snap_left3_right4 = _snap_two_panes((2026, 3), (2026, 4))
        snap_left4_right4 = _snap_two_panes((2026, 4), (2026, 4))
        snap_apply_enabled = _snap_two_panes((2026, 4), (2026, 4), apply_disabled=False)

        stub = StubAbRun([
            snap_left3_right4,  # _nav_pane_to(0): 左是 3 月 → click Next
            snap_left4_right4,  # _nav_pane_to(0): 左已是 4 月 → break
            snap_left4_right4,  # 取 left pane day 1
            snap_left4_right4,  # _nav_pane_to(1): 右已是 4 月
            snap_left4_right4,  # 取 right pane last day
            snap_apply_enabled, # _apply
        ])
        picker = DateRangePicker(stub, sleep_fn=self._noop_sleep)
        result = picker.select_month_range(2026, 4)

        assert result is True
        assert 'click e4' in stub.calls  # Left pane Next month

    def test_left_pane_needs_navigation_backward(self):
        """左 pane 在 5 月，需要點 Prev 倒退到 4 月。"""
        snap_left5_right5 = _snap_two_panes((2026, 5), (2026, 5))
        snap_left4_right4 = _snap_two_panes((2026, 4), (2026, 4))
        snap_apply = _snap_two_panes((2026, 4), (2026, 4))

        stub = StubAbRun([
            snap_left5_right5,  # nav 0: 左是 5 月 → click Prev
            snap_left4_right4,  # nav 0: 左已是 4 月
            snap_left4_right4,  # click day 1
            snap_left4_right4,  # nav 1: 右已是 4 月
            snap_left4_right4,  # click last day
            snap_apply,         # apply
        ])
        picker = DateRangePicker(stub, sleep_fn=self._noop_sleep)
        result = picker.select_month_range(2026, 4)

        assert result is True
        assert 'click e3' in stub.calls  # Left pane Prev month

    def test_apply_initially_disabled_then_enabled(self):
        """套用一開始 disabled，等第二次 snapshot 才 enabled。"""
        snap = _snap_two_panes((2026, 4), (2026, 4))
        snap_disabled = _snap_two_panes((2026, 4), (2026, 4), apply_disabled=True)
        snap_enabled = _snap_two_panes((2026, 4), (2026, 4), apply_disabled=False)

        stub = StubAbRun([
            snap, snap,          # nav 0
            snap,                # click day 1
            snap, snap,          # nav 1
            snap,                # click last day
            snap_disabled,       # apply: disabled
            snap_enabled,        # apply: enabled → click
        ])
        picker = DateRangePicker(stub, sleep_fn=self._noop_sleep)
        result = picker.select_month_range(2026, 4)

        assert result is True
        assert 'click e9' in stub.calls

    def test_day_not_found_returns_false(self):
        """找不到 day 1 的 ref → 回傳 False。"""
        empty_snap = '  - button "getDateText()" [ref=e1]'
        stub = StubAbRun([empty_snap] * 10)
        picker = DateRangePicker(stub, sleep_fn=self._noop_sleep)
        result = picker.select_month_range(2026, 4)
        assert result is False

    def test_apply_never_enabled_returns_false(self):
        """套用始終 disabled → 回傳 False。"""
        snap = _snap_two_panes((2026, 4), (2026, 4))
        snap_disabled = _snap_two_panes((2026, 4), (2026, 4), apply_disabled=True)

        stub = StubAbRun([snap] * 4 + [snap_disabled] * 5)  # 4 snaps for nav+days, rest disabled
        picker = DateRangePicker(stub, sleep_fn=self._noop_sleep)
        result = picker.select_month_range(2026, 4)
        assert result is False
