# -*- coding: utf-8 -*-
"""
⑥ PDFテキスト抽出 → JSON保存

PDFファイルからページ別テキストを抽出し、JSON形式で保存する。
Streamlit Cloud等でキーワード検索するための事前データ作成用。

使い方:
  python "⑥_pdf_text_extractor.py" --target "20260213" --save-root ./pdf_tmp --out-dir ./text_data

出力JSON形式 (1ファイル/日):
  text_20260213.json = {
    "date": "20260213",
    "extracted_at": "2026-02-13T22:00:00",
    "file_count": 120,
    "files": [
      {
        "pdf": "7203_0900_トヨタ_決算短信.pdf",
        "code": "7203",
        "company": "トヨタ自動車",
        "category": "決算短信",
        "url": "https://...",
        "pages": ["テキスト1ページ目...", "テキスト2ページ目...", ...]
      },
      ...
    ]
  }
"""

import os
import re
import json
import argparse
import datetime
import unicodedata
import pandas as pd

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

# ============================================================
# 設定
# ============================================================
DEFAULT_SAVE_ROOT = "./pdf_tmp"
DEFAULT_OUT_DIR = "./text_data"
MAX_RETENTION_DAYS = 180  # 半年分保持


# ============================================================
# ユーティリティ
# ============================================================
def norm_key(s: str) -> str:
    return unicodedata.normalize("NFKC", str(s)).strip()


def extract_code_from_pdf_filename(pdf_filename: str) -> str:
    m = re.match(r"^([0-9A-Za-z]{4})_", str(pdf_filename))
    return m.group(1).upper() if m else ""


PRIORITY_KEYWORDS = ["事業計画", "予想の修正", "決算短信", "説明資料", "月次", "資本コストや株価"]


def get_category(title: str) -> str:
    for kw in PRIORITY_KEYWORDS:
        if kw in title:
            return kw
    return "その他"


def load_tdnet_meta(root_path: str, date_str: str) -> dict:
    """TDnet_Sorted CSV からメタデータ辞書を構築 (key = 正規化PDFファイル名)"""
    day_csv = os.path.join(root_path, date_str, f"TDnet_Sorted_{date_str}.csv")
    root_csv = os.path.join(root_path, f"TDnet_Sorted_{date_str}.csv")
    csv_path = day_csv if os.path.exists(day_csv) else root_csv if os.path.exists(root_csv) else None

    if csv_path is None:
        return {}

    df = pd.read_csv(csv_path, dtype=str).fillna("")
    df.columns = [str(c).strip().replace("\ufeff", "") for c in df.columns]

    if "PDFファイル名" not in df.columns:
        return {}

    index = {}
    for _, r in df.iterrows():
        pdf_key = norm_key(r.get("PDFファイル名", ""))
        if not pdf_key:
            continue

        title_link = str(r.get("表題（リンク）", "")).strip()
        display_text = str(r.get("会社名", "")).strip()
        m = re.match(r'=HYPERLINK\("([^"]*)",\s*"([^"]*)"\)', title_link)
        url = ""
        if m:
            url = m.group(1)
            display_text = m.group(2) or display_text

        bunrui = str(r.get("分類", "")).strip()
        if not bunrui:
            bunrui = get_category(display_text)

        index[pdf_key] = {
            "company": str(r.get("会社名", "")).strip(),
            "code": str(r.get("コード", "")).strip()[:4],
            "category": bunrui,
            "title": display_text,
            "url": url or str(r.get("URL（生）", "")).strip(),
        }

    return index


def extract_text_from_pdf(pdf_path: str) -> list[str]:
    """PDFからページ別テキストをリストで返す"""
    try:
        doc = fitz.open(pdf_path)
        pages = []
        for page in doc:
            text = page.get_text("text").strip()
            pages.append(text)
        doc.close()
        return pages
    except Exception as e:
        print(f"  [WARN] テキスト抽出失敗: {pdf_path} / {e}")
        return []


# ============================================================
# メイン処理
# ============================================================
def extract_date(save_root: str, date_str: str, out_dir: str) -> str:
    """
    1日分のPDFからテキストを抽出してJSONに保存する。
    戻り値: 出力JSONファイルパス
    """
    day_dir = os.path.join(save_root, date_str)
    if not os.path.isdir(day_dir):
        print(f"[WARN] フォルダが見つかりません: {day_dir}")
        return ""

    pdf_files = sorted([f for f in os.listdir(day_dir) if f.lower().endswith(".pdf")])
    if not pdf_files:
        print(f"[WARN] PDFファイルがありません: {day_dir}")
        return ""

    # メタデータ読み込み
    meta_index = load_tdnet_meta(save_root, date_str)

    print(f"[{date_str}] PDF数: {len(pdf_files)}, メタデータ: {len(meta_index)}件")

    files_data = []
    for i, pdf_name in enumerate(pdf_files):
        pdf_path = os.path.join(day_dir, pdf_name)
        pages = extract_text_from_pdf(pdf_path)

        if not pages:
            continue

        code = extract_code_from_pdf_filename(pdf_name)
        pdf_key = norm_key(pdf_name)
        meta = meta_index.get(pdf_key, {})

        files_data.append({
            "pdf": pdf_name,
            "code": code or meta.get("code", ""),
            "company": meta.get("company", ""),
            "category": meta.get("category", "その他"),
            "url": meta.get("url", ""),
            "pages": pages,
        })

        if (i + 1) % 50 == 0:
            print(f"  進捗: {i + 1}/{len(pdf_files)}")

    # JSON出力
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"text_{date_str}.json")

    data = {
        "date": date_str,
        "extracted_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "file_count": len(files_data),
        "files": files_data,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    print(f"  [OK] 保存: {out_path} ({len(files_data)}件, {size_mb:.1f}MB)")

    return out_path


def cleanup_old_files(out_dir: str, max_days: int = MAX_RETENTION_DAYS):
    """古いテキストJSONファイルを削除（半年分のみ保持）"""
    if not os.path.isdir(out_dir):
        return

    cutoff = (datetime.date.today() - datetime.timedelta(days=max_days)).strftime("%Y%m%d")
    removed = 0

    for fn in os.listdir(out_dir):
        m = re.match(r"text_(\d{8})\.json$", fn)
        if m and m.group(1) < cutoff:
            os.remove(os.path.join(out_dir, fn))
            removed += 1

    if removed:
        print(f"[CLEANUP] 古いテキストJSON {removed}件を削除（{cutoff}以前）")


def list_date_folders(root_path: str) -> list[str]:
    if not os.path.isdir(root_path):
        return []
    return sorted([
        d for d in os.listdir(root_path)
        if os.path.isdir(os.path.join(root_path, d)) and re.fullmatch(r"\d{8}", d)
    ])


def parse_args():
    p = argparse.ArgumentParser(description="⑥ PDFテキスト抽出 → JSON保存")
    p.add_argument("--save-root", default=DEFAULT_SAVE_ROOT,
                   help="PDFの保存先ルート（①の出力先）")
    p.add_argument("--target", required=True,
                   help="YYYYMMDD（1日） / 'YYYYMMDD YYYYMMDD'（範囲）/ all（全日付）")
    p.add_argument("--out-dir", default=DEFAULT_OUT_DIR,
                   help="テキストJSON出力先ディレクトリ")
    p.add_argument("--retention-days", type=int, default=MAX_RETENTION_DAYS,
                   help=f"テキストJSONの保持日数（デフォルト: {MAX_RETENTION_DAYS}日）")
    p.add_argument("--skip-existing", action="store_true",
                   help="既に抽出済みの日付はスキップする")
    return p.parse_args()


def main():
    if fitz is None:
        raise RuntimeError("PyMuPDF(fitz)が必要です: pip install pymupdf")

    args = parse_args()
    save_root = args.save_root
    out_dir = args.out_dir

    # 対象日付の決定
    if args.target.strip().lower() == "all":
        target_dates = list_date_folders(save_root)
    elif " " in args.target.strip():
        d1, d2 = args.target.strip().split()
        all_dates = list_date_folders(save_root)
        target_dates = [d for d in all_dates if d1 <= d <= d2]
    else:
        target_dates = [args.target.strip()]

    if not target_dates:
        print("対象日付がありません。")
        return

    print(f"=== ⑥ PDFテキスト抽出 ===")
    print(f"保存先: {save_root}")
    print(f"出力先: {out_dir}")
    print(f"対象日数: {len(target_dates)}")

    extracted = 0
    skipped = 0

    for date_str in target_dates:
        # スキップ判定
        if args.skip_existing:
            existing = os.path.join(out_dir, f"text_{date_str}.json")
            if os.path.exists(existing):
                skipped += 1
                continue

        result = extract_date(save_root, date_str, out_dir)
        if result:
            extracted += 1

    # 古いファイルのクリーンアップ
    cleanup_old_files(out_dir, max_days=args.retention_days)

    print(f"\n[DONE] 完了: 抽出 {extracted}件, スキップ {skipped}件")


if __name__ == "__main__":
    main()
