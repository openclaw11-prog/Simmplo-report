"""
test_integration_daily_report.py

驗證整合後的 fetch_xiaozhun_daily 回傳格式與舊版相同。
@pytest.mark.slow — 需真實 browser。
"""
import sys, os, pytest
sys.path.insert(0, '/Users/simmpo-claw/services')

AB_CMD = "npx --prefix ~/tools/agent-browser agent-browser"
TEST_DATE = '2026-03-07'  # 已知有資料的日期（第一週測試確認過）


@pytest.mark.slow
def test_fetch_xiaozhun_daily_returns_correct_schema():
    from daily_report import fetch_xiaozhun_daily

    result = fetch_xiaozhun_daily(TEST_DATE, agent_browser=AB_CMD)

    print(f'\nresult: {result}')

    # 結構驗證：必要欄位都要有
    assert 'has_data' in result
    assert 'spend' in result
    assert 'purchases' in result
    assert 'purchase_value' in result

    # 資料驗證
    assert result['has_data'] is True, f'預期有資料但 has_data=False: {result}'
    assert result['spend'] == 4549.0,       f"花費應為 4549，實際: {result['spend']}"
    assert result['purchases'] == 8,        f"購買應為 8，實際: {result['purchases']}"
    assert result['purchase_value'] == 9643.0, f"購買轉換值應為 9643，實際: {result['purchase_value']}"


@pytest.mark.slow
def test_fetch_xiaozhun_daily_no_agent_browser():
    from daily_report import fetch_xiaozhun_daily

    result = fetch_xiaozhun_daily(TEST_DATE, agent_browser='')
    assert result['has_data'] is False
    assert 'error' in result
