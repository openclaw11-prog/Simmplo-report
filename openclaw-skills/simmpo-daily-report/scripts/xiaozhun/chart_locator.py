"""
chart_locator.py — 從 agent-browser snapshot 找目標圖表

責任：
  從 snapshot text 評分，選出「廣告成效總預覽 + Date/花費/購買轉換值」那張表。
  純函式，不呼叫 browser。
"""
import re
from dataclasses import dataclass, field
from typing import Optional


_TARGET_SIGNALS = ['廣告成效總預覽', 'Date', '花費', '購買轉換值']
_PAGE_LEVEL_NOISE = ['下載報表', 'PDF', '新增頁面', '分享', '檢視']


@dataclass
class ChartCandidate:
    ref: str
    text: str
    score: int = field(default=0, init=False)

    def __post_init__(self):
        self.score = score_chart_candidate(self.text)


def score_chart_candidate(text: str) -> int:
    score = 0
    for sig in _TARGET_SIGNALS:
        if sig in text:
            score += 10
    for noise in _PAGE_LEVEL_NOISE:
        if noise in text:
            score -= 20
    return score


def pick_best_chart(candidates: list[ChartCandidate]) -> Optional[ChartCandidate]:
    if not candidates:
        return None
    best = max(candidates, key=lambda c: c.score)
    return best if best.score > 0 else None


def extract_candidates_from_snapshot(snapshot: str) -> list[ChartCandidate]:
    """
    從 snapshot 提取候選 chart container。
    把子節點文字累積進父節點，讓父節點也能評到子節點的關鍵字。
    """
    lines = snapshot.splitlines()

    # 收集所有 generic/region/figure 行及其縮排層級
    blocks: list[dict] = []
    for line in lines:
        m = re.match(r'^(\s*)(generic|region|figure)\s+.*\[ref=(e\d+)\]', line)
        if m:
            indent = len(m.group(1))
            blocks.append({'indent': indent, 'ref': m.group(3), 'lines': [line]})
        elif blocks:
            blocks[-1]['lines'].append(line)

    # 對每個 block，把縮排更深的後續 block 文字累積進來
    candidates = []
    for i, block in enumerate(blocks):
        accumulated = list(block['lines'])
        for j in range(i + 1, len(blocks)):
            if blocks[j]['indent'] > block['indent']:
                accumulated.extend(blocks[j]['lines'])
            else:
                break
        candidates.append(ChartCandidate(ref=block['ref'], text='\n'.join(accumulated)))

    return candidates
