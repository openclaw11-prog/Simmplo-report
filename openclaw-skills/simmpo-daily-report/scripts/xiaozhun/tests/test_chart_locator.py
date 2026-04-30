import pytest
import sys
sys.path.insert(0, '/Users/simmpo-claw/services')

from xiaozhun.chart_locator import (
    score_chart_candidate,
    ChartCandidate,
    pick_best_chart,
    extract_candidates_from_snapshot,
)

# 模擬真實 snapshot 的片段
SNAPSHOT_WITH_TARGET = """\
  generic "廣告成效總預覽" [ref=e30]
    generic "Date 花費 曝光次數 購買轉換值" [ref=e32]
      text "Date"
      text "花費"
      text "購買轉換值"
"""

SNAPSHOT_PAGE_LEVEL = """\
  generic "Simmpo - Ads Overview Report" [ref=e10]
    button "下載報表" [ref=e11]
    button "分享" [ref=e12]
"""

SNAPSHOT_MIXED = SNAPSHOT_PAGE_LEVEL + SNAPSHOT_WITH_TARGET


class TestScoreChartCandidate:
    def test_target_text_scores_high(self):
        text = '廣告成效總預覽\nDate\n花費\n購買轉換值'
        assert score_chart_candidate(text) >= 40

    def test_page_level_scores_negative(self):
        text = '下載報表\nPDF\n分享'
        assert score_chart_candidate(text) < 0

    def test_empty_scores_zero(self):
        assert score_chart_candidate('') == 0

    def test_partial_match_scores_proportional(self):
        # 只有 Date 和 花費，沒有購買轉換值
        s1 = score_chart_candidate('Date\n花費')
        s2 = score_chart_candidate('Date\n花費\n購買轉換值')
        assert s2 > s1


class TestPickBestChart:
    def test_picks_highest_score(self):
        c1 = ChartCandidate(ref='e10', text='下載報表')
        c2 = ChartCandidate(ref='e30', text='廣告成效總預覽\nDate\n花費\n購買轉換值')
        result = pick_best_chart([c1, c2])
        assert result is not None
        assert result.ref == 'e30'

    def test_returns_none_if_all_zero_or_negative(self):
        c1 = ChartCandidate(ref='e10', text='some unrelated text')
        result = pick_best_chart([c1])
        assert result is None

    def test_returns_none_for_empty_list(self):
        assert pick_best_chart([]) is None


class TestExtractCandidates:
    def test_extracts_refs(self):
        candidates = extract_candidates_from_snapshot(SNAPSHOT_WITH_TARGET)
        refs = {c.ref for c in candidates}
        assert 'e30' in refs or 'e32' in refs

    def test_picks_target_from_mixed(self):
        candidates = extract_candidates_from_snapshot(SNAPSHOT_MIXED)
        best = pick_best_chart(candidates)
        assert best is not None
        assert '廣告成效總預覽' in best.text
