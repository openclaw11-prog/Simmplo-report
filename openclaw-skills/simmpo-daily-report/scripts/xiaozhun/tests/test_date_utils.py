import pytest
import sys
sys.path.insert(0, '/Users/simmpo-claw/services')

from xiaozhun.date_utils import normalize_looker_date, date_to_looker_label


class TestNormalizeLookerDate:
    def test_chinese_format(self):
        assert normalize_looker_date('2026年3月27日') == '2026-03-27'

    def test_chinese_single_digit(self):
        assert normalize_looker_date('2026年3月1日') == '2026-03-01'

    def test_iso_format(self):
        assert normalize_looker_date('2026-03-27') == '2026-03-27'

    def test_iso_single_digit(self):
        assert normalize_looker_date('2026-3-1') == '2026-03-01'

    def test_slash_yyyy_first(self):
        assert normalize_looker_date('2026/3/27') == '2026-03-27'

    def test_slash_mm_dd_yyyy(self):
        assert normalize_looker_date('3/27/2026') == '2026-03-27'

    def test_slash_mm_dd_yy(self):
        assert normalize_looker_date('3/27/26') == '2026-03-27'

    def test_strips_whitespace(self):
        assert normalize_looker_date('  2026年3月27日  ') == '2026-03-27'

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            normalize_looker_date('not-a-date')


class TestDateToLookerLabel:
    def test_basic(self):
        assert date_to_looker_label('2026-03-27') == '2026年3月27日'

    def test_no_leading_zero_in_label(self):
        # 標籤用自然數字，不補零
        assert date_to_looker_label('2026-03-01') == '2026年3月1日'
