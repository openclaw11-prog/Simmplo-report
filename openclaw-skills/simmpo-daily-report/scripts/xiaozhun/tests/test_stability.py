"""
test_stability.py — 穩定性測試

Step 1: 同一天連跑 3 次，結果要完全一致
Step 2: 昨天的日期（最真實場景）
"""
import sys, subprocess, time, pytest
from datetime import date, timedelta

sys.path.insert(0, '/Users/simmpo-claw/services')

AB_CMD = "npx --prefix ~/tools/agent-browser agent-browser"
KNOWN_DATE = '2026-03-07'
KNOWN_RESULT = {'spend': 4549.0, 'purchases': 8, 'purchase_value': 9643.0, 'has_data': True}


@pytest.mark.slow
@pytest.mark.parametrize('run', [1, 2, 3])
def test_consistency(run):
    """同一天跑 3 次，結果要完全一致。"""
    from daily_report import fetch_xiaozhun_daily
    result = fetch_xiaozhun_daily(KNOWN_DATE, agent_browser=AB_CMD)
    print(f'\n  run={run} result={result}')
    assert result == KNOWN_RESULT, f'run={run} 結果不一致: {result}'


@pytest.mark.slow
def test_yesterday():
    """昨天的日期，不斷言具體數字，只驗結構與有資料或有明確原因。"""
    from daily_report import fetch_xiaozhun_daily
    yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
    print(f'\n  yesterday={yesterday}')
    result = fetch_xiaozhun_daily(yesterday, agent_browser=AB_CMD)
    print(f'  result={result}')
    assert 'has_data' in result
    assert 'spend' in result
    assert 'purchase_value' in result
    if result['has_data']:
        assert result['spend'] > 0
    else:
        assert 'error' in result, '沒有資料時應有 error 說明原因'
