# -*- coding: utf-8 -*-
"""
XBRL分析ExcelファイルをJSON形式にエクスポートする。
GitHub Pages公開用の index.json（一覧）と詳細JSONを生成。

Usage:
  python "⑤_export_json.py"
  python "⑤_export_json.py" --force          # 全ファイル再生成
  python "⑤_export_json.py" --target 20260206 # 特定日付のみ
"""

import os, sys, re, json, math, argparse
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

DATA_ROOT = os.environ.get(
    "XBRL_DATA_ROOT",
    os.path.join(os.path.expanduser("~"), "Desktop", "XBRL_Data"),
)
DOCS_DIR = Path(__file__).parent / "docs"
DATA_DIR = DOCS_DIR / "data"
DETAIL_DIR = DATA_DIR / "detail"

SALES_LABELS = {'売上高', '売上収益（IFRS）', '営業収益'}


def safe_val(v):
    """JSON互換の値に変換"""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    return str(v)


def read_summary(p):
    """Excelからサマリー情報を読み取る（一覧用）"""
    from openpyxl import load_workbook
    info = {'title': '', 'op_cur': None, 'op_prev': None, 'op_diff': None, 'rev_chg': None}
    try:
        wb = load_workbook(str(p), read_only=True, data_only=True)
        ws = wb[wb.sheetnames[0]]
        info['title'] = str(ws.cell(row=3, column=2).value or '')

        for row in ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=4):
            if '営業利益率' in str(row[0].value or ''):
                for k, i in [('op_cur', 1), ('op_prev', 2), ('op_diff', 3)]:
                    v = row[i].value
                    info[k] = round(float(v), 2) if v is not None else None
                break

        # 売上高の増減率（増収率）
        for sn in wb.sheetnames[1:]:
            ws2 = wb[sn]
            hdr = [str(c.value or '') for c in next(ws2.iter_rows(min_row=1, max_row=1))]
            ri = None
            for i, h in enumerate(hdr):
                if '増減率' in h:
                    ri = i
                    break
            if ri is None:
                continue
            for row in ws2.iter_rows(min_row=2, max_row=ws2.max_row):
                label = str(row[0].value or '').strip()
                if label in SALES_LABELS:
                    v = row[ri].value
                    if v is not None:
                        info['rev_chg'] = round(float(v) * 100, 2)
                    break
            if info['rev_chg'] is not None:
                break
        wb.close()
    except Exception as e:
        print(f"  Warning (summary): {e}")
    return info


def read_all_sheets(p):
    """Excelの全シートを読み取り、JSON互換のデータに変換"""
    from openpyxl import load_workbook
    wb = load_workbook(str(p), data_only=True)
    sheets = {}
    for name in wb.sheetnames:
        ws = wb[name]
        rows = []
        for row in ws.iter_rows(max_row=ws.max_row, max_col=ws.max_column, values_only=True):
            rows.append([safe_val(v) for v in row])
        sheets[name] = rows
    wb.close()
    return sheets


def main():
    parser = argparse.ArgumentParser(description="Excel→JSON変換")
    parser.add_argument("--force", action="store_true", help="全ファイルを再生成")
    parser.add_argument("--target", type=str, help="特定日付のみ処理 (例: 20260206)")
    args = parser.parse_args()

    root = Path(DATA_ROOT)
    if not root.exists():
        print(f"データディレクトリが見つかりません: {DATA_ROOT}")
        return

    DETAIL_DIR.mkdir(parents=True, exist_ok=True)

    index_entries = []
    generated = 0
    skipped = 0

    for dd in sorted(root.iterdir()):
        if not dd.is_dir() or not re.fullmatch(r'\d{8}', dd.name):
            continue
        d = dd.name
        if args.target and d != args.target:
            continue

        print(f"[{d}]")
        seen = {}

        for xf in sorted(dd.glob("XBRL*_*.xlsx")):
            m = re.match(r'XBRL[^_]*_([^_]+)_(.+)', xf.stem)
            if not m:
                continue
            code, company = m.group(1), m.group(2)

            # 詳細JSONファイル名（同一日付+コードの重複対応）
            base_key = f"{d}_{code}"
            if base_key in seen:
                seen[base_key] += 1
                detail_name = f"{base_key}_{seen[base_key]}.json"
            else:
                seen[base_key] = 0
                detail_name = f"{base_key}.json"

            # サマリー情報取得
            s = read_summary(xf)

            index_entries.append({
                'date': f"{d[:4]}/{d[4:6]}/{d[6:]}",
                'date_raw': d,
                'code': code,
                'company': company,
                'title': s['title'],
                'rev_chg': safe_val(s['rev_chg']),
                'op_cur': safe_val(s['op_cur']),
                'op_prev': safe_val(s['op_prev']),
                'op_diff': safe_val(s['op_diff']),
                'detail': detail_name,
            })

            # 詳細JSON生成（更新チェック）
            detail_path = DETAIL_DIR / detail_name
            excel_mtime = xf.stat().st_mtime
            need_update = args.force or not detail_path.exists()
            if not need_update and detail_path.exists():
                if detail_path.stat().st_mtime < excel_mtime:
                    need_update = True

            if need_update:
                try:
                    sheets = read_all_sheets(xf)
                    with open(detail_path, 'w', encoding='utf-8') as f:
                        json.dump({'sheets': sheets}, f, ensure_ascii=False)
                    print(f"  + {detail_name}")
                    generated += 1
                except Exception as e:
                    print(f"  ERROR {xf.name}: {e}")
            else:
                skipped += 1

    # index.json出力（常に再生成）
    index_path = DATA_DIR / "index.json"
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index_entries, f, ensure_ascii=False, indent=2)

    print(f"\n完了: {len(index_entries)}件")
    print(f"  詳細JSON: 生成={generated}, スキップ={skipped}")
    print(f"  出力先: {DATA_DIR}")


if __name__ == "__main__":
    main()
