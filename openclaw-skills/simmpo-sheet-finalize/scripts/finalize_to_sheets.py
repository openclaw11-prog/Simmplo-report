#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
from datetime import datetime, timezone, timedelta

_TZ_TAIPEI = timezone(timedelta(hours=8))


def now_taipei(fmt="%Y-%m-%d %H:%M:%S"):
    """Return current Asia/Taipei time. All logs use Taipei time (UTC+8) exclusively."""
    return datetime.now(_TZ_TAIPEI).strftime(fmt)

SPREADSHEET_ID = "1fNw7BYrVZ6UCzcUOJanbkU5m5FAYzpQ1DwdherjsOOY"
LOG_SHEET_NAME = "cron_log"

_GWS_ENV = os.environ.copy()
_GWS_ENV.setdefault("GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE",
                    os.path.expanduser("~/.config/gws/user_credentials.json"))
_GWS_ENV.setdefault("GOOGLE_WORKSPACE_CLI_KEYRING_BACKEND", "file")


def get_sheet_name(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime("%Y-%m")


def get_column_letter(n):
    string = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        string = chr(65 + remainder) + string
    return string


def list_sheets():
    cmd = [
        "gws", "sheets", "spreadsheets", "get",
        "--params", json.dumps({"spreadsheetId": SPREADSHEET_ID,
                                "fields": "sheets.properties"})
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, env=_GWS_ENV)
    if result.returncode != 0:
        return []
    data = json.loads(result.stdout)
    return [(s["properties"]["title"], s["properties"]["sheetId"])
            for s in data.get("sheets", [])]


def get_sheet_id(sheet_name):
    for title, sid in list_sheets():
        if title == sheet_name:
            return sid
    return None


def create_sheet(title):
    print(f"Creating sheet tab: {title}")
    cmd = [
        "gws", "sheets", "spreadsheets", "batchUpdate",
        "--params", json.dumps({"spreadsheetId": SPREADSHEET_ID}),
        "--json", json.dumps({"requests": [{"addSheet": {"properties": {"title": title}}}]})
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, env=_GWS_ENV)
    if result.returncode != 0:
        # Sheet may already exist (list_sheets transient failure); treat as non-fatal
        if "已有工作表" in result.stderr or "already exists" in result.stderr.lower():
            print(f"Sheet '{title}' already exists, skipping creation.")
            return
        raise SystemExit(f"Failed to create sheet '{title}': {result.stderr}")

    # Write row labels for new monthly tab
    labels = [
        ["", "類別", "渠道"],
        ["", "", ""],
        ["", "官網", "官網（台灣）金額未稅"],
        ["", "", "官網（台灣）含稅"],
        ["", "", "官網（香港）"],
        ["", "", "官網（澳門）"],
        ["", "", "官網（馬來）"],
        ["", "", "官網（新加坡）"],
        ["", "Google Ads", "Google Ads"],
        ["", "FB廣告", "FB廣告（域動）"],
        ["", "", "FB廣告（肖準）實際投放"],
        ["", "", "FB廣告（肖準）10% 服務費"],
    ]
    params = {
        "spreadsheetId": SPREADSHEET_ID,
        "range": f"{title}!A1:C12",
        "valueInputOption": "USER_ENTERED"
    }
    cmd = [
        "gws", "sheets", "spreadsheets", "values", "update",
        "--params", json.dumps(params),
        "--json", json.dumps({"values": labels})
    ]
    subprocess.run(cmd, capture_output=True, text=True, env=_GWS_ENV)
    print(f"Created sheet tab: {title}")


def ensure_sheet_exists(title):
    if title not in [t for t, _ in list_sheets()]:
        create_sheet(title)


def ensure_enough_columns(sheet_name, needed_col_idx):
    """Append columns to the sheet if it doesn't have enough to fit needed_col_idx."""
    cmd = [
        "gws", "sheets", "spreadsheets", "get",
        "--params", json.dumps({
            "spreadsheetId": SPREADSHEET_ID,
            "fields": "sheets(properties(title,sheetId,gridProperties))"
        })
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, env=_GWS_ENV)
    if result.returncode != 0:
        print(f"Warning: could not read sheet grid properties: {result.stderr}")
        return
    data = json.loads(result.stdout)
    sheet_id = None
    current_cols = None
    for s in data.get("sheets", []):
        if s["properties"]["title"] == sheet_name:
            sheet_id = s["properties"]["sheetId"]
            current_cols = s["properties"].get("gridProperties", {}).get("columnCount", 26)
            break
    if sheet_id is None:
        print(f"Warning: sheet '{sheet_name}' not found when checking column count")
        return
    if current_cols >= needed_col_idx + 1:
        return
    append_count = needed_col_idx + 10 - current_cols  # add buffer
    print(f"  Expanding '{sheet_name}' from {current_cols} to {current_cols + append_count} columns")
    request = {
        "appendDimension": {
            "sheetId": sheet_id,
            "dimension": "COLUMNS",
            "length": append_count
        }
    }
    cmd = [
        "gws", "sheets", "spreadsheets", "batchUpdate",
        "--params", json.dumps({"spreadsheetId": SPREADSHEET_ID}),
        "--json", json.dumps({"requests": [request]})
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, env=_GWS_ENV)
    if result.returncode != 0:
        print(f"Warning: failed to expand columns: {result.stderr}")
    else:
        print(f"  ✓ Expanded columns to {current_cols + append_count}")


def merge_row1_cells(sheet_name, rev_col_idx):
    """Merge row 1 cells for the new column pair (rev + ads) to match existing format."""
    sheet_id = get_sheet_id(sheet_name)
    if sheet_id is None:
        print(f"Warning: could not get sheetId for '{sheet_name}', skipping merge")
        return
    # Sheets API uses 0-based indices; row 1 = rowIndex 0
    col_start = rev_col_idx - 1        # 0-based
    col_end   = rev_col_idx + 1        # exclusive (covers rev + ads)
    request = {
        "mergeCells": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 1,
                "startColumnIndex": col_start,
                "endColumnIndex": col_end
            },
            "mergeType": "MERGE_ALL"
        }
    }
    cmd = [
        "gws", "sheets", "spreadsheets", "batchUpdate",
        "--params", json.dumps({"spreadsheetId": SPREADSHEET_ID}),
        "--json", json.dumps({"requests": [request]})
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, env=_GWS_ENV)
    if result.returncode != 0:
        print(f"Warning: merge failed: {result.stderr}")
    else:
        print(f"  ✓ Merged row 1 cols {get_column_letter(rev_col_idx)}:{get_column_letter(rev_col_idx+1)}")


def gws_get_range(sheet_name, range_ref):
    cmd = [
        "gws", "sheets", "spreadsheets", "values", "get",
        "--params", json.dumps({
            "spreadsheetId": SPREADSHEET_ID,
            "range": f"{sheet_name}!{range_ref}"
        })
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, env=_GWS_ENV)
    if result.returncode != 0:
        return []
    data = json.loads(result.stdout)
    return data.get("values", [])


def find_row_mapping(sheet_name):
    """
    Reads cols A–C to discover which row each metric lives on.
    Falls back to defaults if a label is not found.
    """
    rows = gws_get_range(sheet_name, "A1:C30")

    mapping = {
        "tw_ex_tax": None,   # 官網（台灣）金額未稅  — rev=tw_ex_tax, ads=meta_spend
        "tw_rev":    None,   # 官網（台灣）含稅      — rev=tw_rev
        "hk_rev":    None,   # 官網（香港）          — rev=hk_rev
        "mo_rev":    None,   # 官網（澳門）          — rev=mo_rev
        "sg_rev":    None,   # 官網（新加坡）        — rev=sg_rev
        "gads":      None,   # Google Ads            — rev=gads_rev, ads=gads_spend
        "fb_domain": None,   # FB廣告（域動）        — rev=0, ads=0
        "xz":        None,   # FB廣告（肖準）實際投放 — rev=xz_rev, ads=xz_spend
    }

    for idx, row in enumerate(rows, 1):
        label = " ".join(cell.strip() for cell in row if cell.strip())
        if not label:
            continue
        if "未稅" in label and ("台灣" in label or "TW" in label):
            mapping["tw_ex_tax"] = idx
        elif "含稅" in label and ("台灣" in label or "TW" in label):
            mapping["tw_rev"] = idx
        elif "香港" in label:
            mapping["hk_rev"] = idx
        elif "澳門" in label:
            mapping["mo_rev"] = idx
        elif "新加坡" in label:
            mapping["sg_rev"] = idx
        elif "google" in label.lower() and "ads" in label.lower():
            mapping["gads"] = idx
        elif "域動" in label:
            mapping["fb_domain"] = idx
        elif "肖準" in label and "實際" in label:
            mapping["xz"] = idx

    defaults = {"tw_ex_tax": 3, "tw_rev": 4, "hk_rev": 5,
                "mo_rev": 6, "sg_rev": 7, "gads": 8, "fb_domain": 9, "xz": 10}
    for key, default in defaults.items():
        if mapping[key] is None:
            print(f"Warning: row for '{key}' not found, using default row {default}")
            mapping[key] = default

    print(f"Row mapping: {mapping}")
    return mapping


def normalize_header_variants(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    y, m, d = dt.year, dt.month, dt.day
    return [
        f"{m}/{d}",
        f"{y}/{m}/{d}",
        f"{y}-{m:02d}-{d:02d}",
        f"{y}/{m:02d}/{d:02d}",
    ]


def find_date_columns(sheet_name, date_str):
    """
    Returns (rev_col_idx, ads_col_idx, is_update, existing_header).

    Reads row 1 as sole source of truth:
    - Plain date found → data already written → add new update column pair AFTER the existing pair (non-destructive)
    - Not found → first write → add plain date header to new column pair
    Each date occupies TWO consecutive columns (rev + ads), so updates always start at last_known_col + 2.
    """
    row1 = gws_get_range(sheet_name, "1:1")
    row = row1[0] if row1 else []
    variants = normalize_header_variants(date_str)

    plain_col_idx = None     # index of the original plain date header
    last_date_col_idx = None  # index of the rightmost column (plain or updated) for this date

    for idx, cell in enumerate(row, start=1):
        value = (cell or "").strip()
        is_plain = value in variants or any(v in value and "updated" not in value for v in variants)
        is_updated = any(v in value for v in variants) and "updated" in value

        if is_plain and "updated" not in value:
            plain_col_idx = idx
            last_date_col_idx = idx
        elif is_updated:
            last_date_col_idx = idx

    dt = datetime.strptime(date_str, "%Y-%m-%d")

    if plain_col_idx is not None:
        # Each column pair = rev + ads (2 cols). Next pair starts at last_date_col_idx + 2.
        next_col_idx = last_date_col_idx + 2
        ensure_enough_columns(sheet_name, next_col_idx + 1)
        new_col = get_column_letter(next_col_idx)
        ads_col = get_column_letter(next_col_idx + 1)
        ts = now_taipei("%H:%M")
        header = f"{dt.month}/{dt.day} (updated {ts})"
        run_gws_update(sheet_name, f"{new_col}1", [[header]])
        run_gws_update(sheet_name, f"{new_col}2:{ads_col}2", [["營業額", "廣告費"]])
        merge_row1_cells(sheet_name, next_col_idx)
        print(f"Date {date_str} found in row 1 — update column {new_col}/{ads_col} ({header})")
        return next_col_idx, next_col_idx + 1, True, row[plain_col_idx - 1]

    # Date not in row 1 → first write
    # +2 because trailing empty ads column is stripped by Sheets API,
    # so len(row) points to last date header; its paired ads col is +1, next free is +2
    next_col_idx = len(row) + 2
    ensure_enough_columns(sheet_name, next_col_idx + 1)
    new_col = get_column_letter(next_col_idx)
    ads_col = get_column_letter(next_col_idx + 1)
    header = f"{dt.month}/{dt.day}"
    run_gws_update(sheet_name, f"{new_col}1", [[header]])
    run_gws_update(sheet_name, f"{new_col}2:{ads_col}2", [["營業額", "廣告費"]])
    merge_row1_cells(sheet_name, next_col_idx)
    print(f"First write for {date_str} → column {new_col}/{ads_col} ({header})")
    return next_col_idx, next_col_idx + 1, False, None


def run_gws_update(sheet_name, range_name, values):
    params = {
        "spreadsheetId": SPREADSHEET_ID,
        "range": f"{sheet_name}!{range_name}",
        "valueInputOption": "USER_ENTERED"
    }
    cmd = [
        "gws", "sheets", "spreadsheets", "values", "update",
        "--params", json.dumps(params),
        "--json", json.dumps({"values": values})
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, env=_GWS_ENV)
    if result.returncode != 0:
        print(f"Error writing {range_name}: {result.stderr}")
    else:
        print(f"  ✓ {range_name} = {values}")


def append_cron_log(date_str, status, summary="", old_tw=""):
    ensure_sheet_exists(LOG_SHEET_NAME)
    ts = now_taipei()
    old_info = f" | 原值 TW={old_tw}" if old_tw else ""
    row = [[ts, date_str, status, summary + old_info]]
    params = {
        "spreadsheetId": SPREADSHEET_ID,
        "range": f"{LOG_SHEET_NAME}!A:D",
        "valueInputOption": "USER_ENTERED",
        "insertDataOption": "INSERT_ROWS"
    }
    cmd = [
        "gws", "sheets", "spreadsheets", "values", "append",
        "--params", json.dumps(params),
        "--json", json.dumps({"values": row})
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, env=_GWS_ENV)
    if result.returncode != 0:
        print(f"cron_log error: {result.stderr}")
    else:
        print(f"cron_log: {ts} | {date_str} | {status}")


def write_data(sheet_name, rev_col, ads_col, rows, tw_ex_tax, tw_rev,
               hk_rev, mo_rev, sg_rev, meta_spend, gads_rev, gads_spend, xz_rev, xz_spend):
    run_gws_update(sheet_name, f"{rev_col}{rows['tw_ex_tax']}:{ads_col}{rows['tw_ex_tax']}",
                   [[str(tw_ex_tax), str(meta_spend)]])
    run_gws_update(sheet_name, f"{rev_col}{rows['tw_rev']}", [[str(tw_rev)]])
    run_gws_update(sheet_name, f"{rev_col}{rows['hk_rev']}", [[str(hk_rev)]])
    run_gws_update(sheet_name, f"{rev_col}{rows['mo_rev']}", [[str(mo_rev)]])
    run_gws_update(sheet_name, f"{rev_col}{rows['sg_rev']}", [[str(sg_rev)]])
    run_gws_update(sheet_name, f"{rev_col}{rows['gads']}:{ads_col}{rows['gads']}",
                   [[str(gads_rev), str(gads_spend)]])
    run_gws_update(sheet_name, f"{rev_col}{rows['fb_domain']}:{ads_col}{rows['fb_domain']}",
                   [["0", "0"]])
    run_gws_update(sheet_name, f"{rev_col}{rows['xz']}:{ads_col}{rows['xz']}",
                   [[str(xz_rev), str(xz_spend)]])


def float_or_failed(value):
    if value == "failed":
        return "failed"
    return float(value)


SHELL_LOG = os.path.expanduser("~/services/simmpo_auto_report.log")


def append_shell_log(line):
    with open(SHELL_LOG, "a") as f:
        f.write(line + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--data-file", help="Path to report JSON")
    parser.add_argument("--failed", action="store_true", help="Mark all cells as failed")
    parser.add_argument("--manual", action="store_true", help="手動補跑，寫入 shell log 並標註")
    parser.add_argument("--tw-revenue", type=float_or_failed)
    parser.add_argument("--hk-revenue", type=float_or_failed)
    parser.add_argument("--mo-revenue", type=float_or_failed)
    parser.add_argument("--sg-revenue", type=float_or_failed)
    parser.add_argument("--meta-spend", type=float_or_failed)
    parser.add_argument("--gads-revenue", type=float_or_failed)
    parser.add_argument("--gads-spend", type=float_or_failed)
    parser.add_argument("--xz-revenue", type=float_or_failed)
    parser.add_argument("--xz-spend", type=float_or_failed)
    args = parser.parse_args()

    if args.manual:
        ts = now_taipei()
        append_shell_log("========================================")
        append_shell_log(f"[{ts}] 開始執行 {args.date} 報表（手動補跑）")

    sheet_name = get_sheet_name(args.date)
    ensure_sheet_exists(sheet_name)
    rows = find_row_mapping(sheet_name)

    rev_col_idx, ads_col_idx, is_update, old_value = find_date_columns(sheet_name, args.date)
    rev_col = get_column_letter(rev_col_idx)
    ads_col = get_column_letter(ads_col_idx)

    if args.failed:
        label = "UPDATE→FAILED" if is_update else "FAILED"
        print(f"Date: {args.date} → Sheet: {sheet_name}, Cols: {rev_col}/{ads_col} ({label})")
        failed_val = "failed"
        write_data(sheet_name, rev_col, ads_col, rows,
                   failed_val, failed_val, failed_val, failed_val, failed_val,
                   failed_val, failed_val, failed_val, failed_val, failed_val)
        append_cron_log(args.date, label, "抓取失敗", old_value or "")
        if args.manual:
            ts = now_taipei()
            append_shell_log(f"[{ts}] 執行完畢（手動補跑，FAILED）")
        return

    data = {}
    if args.data_file:
        with open(args.data_file, 'r') as f:
            data = json.load(f)

    tw_rev   = args.tw_revenue   if args.tw_revenue   is not None else data.get("shopline", {}).get("TW", {}).get("total", 0)
    hk_rev   = args.hk_revenue   if args.hk_revenue   is not None else data.get("shopline", {}).get("HK", {}).get("total", 0)
    mo_rev   = args.mo_revenue   if args.mo_revenue   is not None else data.get("shopline", {}).get("MO", {}).get("total", 0)
    sg_rev   = args.sg_revenue   if args.sg_revenue   is not None else data.get("shopline", {}).get("SG", {}).get("total", 0)
    meta_spend  = args.meta_spend   if args.meta_spend   is not None else data.get("meta_total", 0)
    gads_rev = args.gads_revenue if args.gads_revenue is not None else data.get("google_ads", {}).get("value", 0)
    gads_spend = args.gads_spend if args.gads_spend   is not None else data.get("google_ads", {}).get("spend", 0)
    xz_rev   = args.xz_revenue   if args.xz_revenue   is not None else data.get("xiaozhun", {}).get("purchase_value", 0)
    xz_spend = args.xz_spend     if args.xz_spend     is not None else data.get("xiaozhun", {}).get("spend", 0)

    tw_ex_tax = round(tw_rev / 1.05) if tw_rev != "failed" else "failed"
    label = "UPDATE" if is_update else "SUCCESS"

    print(f"Date: {args.date} → Sheet: {sheet_name}, Cols: {rev_col}/{ads_col} ({label})")
    write_data(sheet_name, rev_col, ads_col, rows,
               tw_ex_tax, tw_rev, hk_rev, mo_rev, sg_rev,
               meta_spend, gads_rev, gads_spend, xz_rev, xz_spend)

    summary = (f"TW={tw_rev} HK={hk_rev} MO={mo_rev} Meta={meta_spend} "
               f"GAds_rev={gads_rev} GAds_spend={gads_spend} XZ_rev={xz_rev} XZ_spend={xz_spend}")
    append_cron_log(args.date, label, summary, old_value or "")
    if args.manual:
        ts = now_taipei()
        append_shell_log(f"[{ts}] {args.date} 報表完成寫入 Sheets（手動補跑）: {summary}")
        append_shell_log(f"[{ts}] 執行完畢")


if __name__ == "__main__":
    main()
