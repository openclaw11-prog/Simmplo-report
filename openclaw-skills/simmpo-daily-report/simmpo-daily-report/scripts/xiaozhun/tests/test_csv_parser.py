import pytest
import sys
sys.path.insert(0, '/Users/simmpo-claw/services')

from xiaozhun.csv_parser import parse_looker_csv

# 真實 CSV 格式：數字含逗號時有引號（Looker Studio 預設輸出）
SAMPLE_CSV = (
    'Date,花費,曝光次數,觸及人數,連結點擊次數,CPC,點擊率,加到購物車,購買,CPA,購買轉換值,客單價,ROAS\n'
    '2026年3月1日,"$3,314","26,170","17,918",113,$29,0.43%,11,6,$552,"$13,683","$2,280.5",4.13\n'
    '2026年3月2日,"$4,395","29,834","18,633",129,$34,0.43%,24,7,$628,"$18,434","$2,633.43",4.19\n'
    '2026年3月7日,"$4,549","34,211","26,645",155,$29,0.45%,25,8,$569,"$9,643","$1,205.38",2.12\n'
)

SAMPLE_CSV_DOLLAR = (
    'Date,花費,購買,購買轉換值\n'
    '2026年3月1日,"$3,314",6,"$13,683"\n'
)

SAMPLE_CSV_PLAIN = (
    'Date,花費,購買,購買轉換值\n'
    '2026年3月1日,3314,6,13683\n'
)


class TestParseLookerCsv:
    def test_finds_target_date(self):
        r = parse_looker_csv(SAMPLE_CSV, '2026-03-01')
        assert r['has_data'] is True
        assert r['spend'] == 3314.0

    def test_purchase_value(self):
        r = parse_looker_csv(SAMPLE_CSV, '2026-03-01')
        assert r['purchase_value'] == 13683.0

    def test_purchases_count(self):
        r = parse_looker_csv(SAMPLE_CSV, '2026-03-01')
        assert r['purchases'] == 6

    def test_mid_month_date(self):
        r = parse_looker_csv(SAMPLE_CSV, '2026-03-07')
        assert r['has_data'] is True
        assert r['spend'] == 4549.0

    def test_date_not_found(self):
        r = parse_looker_csv(SAMPLE_CSV, '2026-03-31')
        assert r['has_data'] is False
        assert 'error' in r

    def test_dollar_sign_stripped(self):
        r = parse_looker_csv(SAMPLE_CSV_DOLLAR, '2026-03-01')
        assert r['spend'] == 3314.0

    def test_plain_numbers(self):
        r = parse_looker_csv(SAMPLE_CSV_PLAIN, '2026-03-01')
        assert r['spend'] == 3314.0

    def test_empty_csv(self):
        r = parse_looker_csv('Date,花費\n', '2026-03-01')
        assert r['has_data'] is False
