# -*- coding: utf-8 -*-
"""
② フリーワード検索（②A:PDF全文検索 / ②B:配布用CSV作成）

【Windowsローカル実行版】
- Colab専用の `!pip` / `google.colab` / `/content/drive` 依存を除去
- 保存先をローカル/ドライブパスに対応（デフォルト: G:\\マイドライブ\\TDnet_Downloads）

使い方（コピペ用デフォルト）:
  ②A（全文検索: PDF本文に対するフリーワード検索）:
    
python "②a②bは２つフリーワード検索.py" analyze --target "20260204" --keywords "価格交渉" "増産" "価格改定" "価格転嫁" "値上" "想定以上" "上方修正" "下方修正" "想定以下" "未達" "大幅" "計画を上" "計画を下" "計画以" "需要回復" "需要の回復" "需要が増" "需要が低" "悪化" "グローバルニッチトップ" "トップシェア" "シェ ア拡大" "レアアース"
  ②B（配布用CSV作成: ①のCSVと②A結果を突合）:
    - 配布用（標準・配布先フォルダ向け / TDnetリンク版）:
        python "②a②bは２つフリーワード検索.py" distribute --target "20260204"

    - 自分用（ローカルPDFへのリンク版 / ダウンロードフォルダ指定）:
        python "②a②bは２つフリーワード検索.py" distribute --target "20260204" --save-root "G:\\マイドライブ\\TDnet_Downloads" --local-link

    ※ --local-link の有無に関わらず、出力CSVには以下の3列が常に含まれます:
      - 「表題（リンク）」: --local-link指定時はローカル、なければTDnet
      - 「表題（リンク_TDnet）」: 常にTDnetへのリンク
      - 「表題（リンク_ローカル）」: 常にローカルPDFへのリンク
    つまり、どちらのコマンドでも両方のリンクが含まれたCSVが出力されます。

  表題検索（①のCSVの「表題」に対する部分一致検索・高速）:
    例）表題に「資本コストや株価を意識した」を含むものをリスト化:
        python "②a②bは２つフリーワード検索.py" title --target "20260204" --keywords "資本コストや株価を意識した"
"""

import os
import re
import pandas as pd
import datetime
import unicodedata
import shutil
import argparse
from pathlib import Path

try:
    import fitz  # PyMuPDF
except Exception as e:
    fitz = None
    _FITZ_IMPORT_ERROR = e

DEFAULT_SAVE_ROOT = r"G:\マイドライブ\TDnet_Downloads"
DEFAULT_TARGET_SPEC = "20251212 20260202"
DEFAULT_SEARCH_KEYWORDS = ["価格交渉", "増産"]
PAGES_SEPARATOR = " "
ANALYSIS_CSV_PREFIX = "Analysis_Hits_free_word"
DISTRIBUTION_CSV_PREFIX = "PDF_Search_Result_Distribution_free_word"
TITLE_SEARCH_CSV_PREFIX = "Title_Hits_free_word"

# -----------------------------
# 日付指定処理
# -----------------------------
def parse_target_spec(spec: str):
    spec = spec.strip()
    parts = spec.split()

    if len(parts) == 1:
        s = parts[0]
        if re.fullmatch(r"\d{8}", s):
            return s, s, s, "day"
        if re.fullmatch(r"\d{6}", s):
            y = int(s[:4]); m = int(s[4:6])
            start = datetime.date(y, m, 1)
            if m == 12:
                end = datetime.date(y + 1, 1, 1) - datetime.timedelta(days=1)
            else:
                end = datetime.date(y, m + 1, 1) - datetime.timedelta(days=1)
            return start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), s, "month"
        raise ValueError("TARGET_SPEC は 'YYYYMMDD' / 'YYYYMM' / 'YYYYMMDD YYYYMMDD' のいずれかです。")

    if len(parts) == 2:
        d1, d2 = parts
        if not (re.fullmatch(r"\d{8}", d1) and re.fullmatch(r"\d{8}", d2)):
            raise ValueError("範囲指定は 'YYYYMMDD YYYYMMDD' 形式で指定してください。")
        if d1 > d2:
            d1, d2 = d2, d1
        return d1, d2, f"{d1}_{d2}", "range"

    raise ValueError("TARGET_SPEC の指定が不正です。")

def list_date_folders(root_path: str):
    if not os.path.isdir(root_path):
        return []
    return sorted([
        d for d in os.listdir(root_path)
        if os.path.isdir(os.path.join(root_path, d)) and re.fullmatch(r"\d{8}", d)
    ])

def select_target_folders(root_path: str, target_spec: str):
    d_from, d_to, label, mode = parse_target_spec(target_spec)
    targets = [d for d in list_date_folders(root_path) if d_from <= d <= d_to]
    return targets, label, (d_from, d_to), mode

# -----------------------------
# PDF解析（キーワード・ページ数・ページ番号）
# -----------------------------
def extract_hits_pages_from_pdf(pdf_path: str, keywords, pages_sep=" "):
    """
    戻り値:
      dict[str, str]  -- キーワード -> ヒットページ番号文字列
      例: {"増産": "3 5", "上方修正": "11 15", "シェア拡大": ""}
      ヒットなしのキーワードは空文字列。
    """
    try:
        doc = fitz.open(pdf_path)

        kw_pages = {kw: set() for kw in keywords}

        for page_index, page in enumerate(doc, start=1):
            text = page.get_text("text")
            for kw in keywords:
                if kw in text:
                    kw_pages[kw].add(page_index)

        doc.close()

        return {
            kw: pages_sep.join(str(p) for p in sorted(pages))
            for kw, pages in kw_pages.items()
        }

    except Exception as e:
        print(f"解析失敗: {pdf_path} / {e}")
        return {kw: "" for kw in keywords}

# -----------------------------
# アーカイブ処理用
# -----------------------------

def archive_if_exists(path: str):
    if not os.path.exists(path):
        return

    base_dir = os.path.dirname(path)
    base_name = os.path.basename(path)

    archive_dir = os.path.join(base_dir, "archive")
    os.makedirs(archive_dir, exist_ok=True)

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    name, ext = os.path.splitext(base_name)

    archived_name = f"{name}_{ts}{ext}"
    archived_path = os.path.join(archive_dir, archived_name)

    shutil.move(path, archived_path)
    print(f"🗂 既存ファイルをアーカイブへ退避: {archived_name}")

# -----------------------------
# コード抽出（①の命名規則前提）
# -----------------------------
def extract_code_from_pdf_filename(pdf_filename: str) -> str:
    m = re.match(r"^([0-9A-Za-z]{4})_", str(pdf_filename))
    return m.group(1).upper() if m else ""

REQUIRED_META_FIELDS = ["分類", "時刻", "コード", "会社名", "表題（リンク）", "URL（生）"]


def norm_key(s: str) -> str:
    return unicodedata.normalize("NFKC", str(s)).strip()


def find_empty_fields(meta: dict, required_fields):
    return [k for k in required_fields if not (meta.get(k, "") or "").strip()]


def build_tdnet_index_for_dates(root_path: str, dates):
    """
    ①のCSVを読み込んで突合用インデックスを作成
    key = (日付, 正規化PDFファイル名)
    """
    index = {}
    missing_csv_dates = []

    for d in sorted(set(dates)):
        day_csv = os.path.join(root_path, d, f"TDnet_Sorted_{d}.csv")
        root_csv = os.path.join(root_path, f"TDnet_Sorted_{d}.csv")
        csv_path = day_csv if os.path.exists(day_csv) else root_csv if os.path.exists(root_csv) else None

        if csv_path is None:
            missing_csv_dates.append(d)
            continue

        df = pd.read_csv(csv_path, dtype=str).fillna("")
        df.columns = [str(c).strip().replace("\ufeff", "") for c in df.columns]

        if "PDFファイル名" not in df.columns:
            raise ValueError(f"{csv_path} に PDFファイル名 列がありません。")

        for _, r in df.iterrows():
            pdf_raw = r.get("PDFファイル名", "")
            pdf_key = norm_key(pdf_raw)
            if not pdf_key:
                continue

            index[(d, pdf_key)] = {
                "分類": r.get("分類", "").strip(),
                "時刻": r.get("時刻", "").strip(),
                "コード": (r.get("コード", "").strip()[:4]),
                "会社名": r.get("会社名", "").strip(),
                "表題（リンク）": r.get("表題（リンク）", "").strip(),
                "URL（生）": r.get("URL（生）", "").strip(),
            }

    return index, missing_csv_dates


def run_title_search(root_dir: str, target_spec: str, keywords):
    """
    ①のCSV（TDnet_Sorted_YYYYMMDD.csv）の「表題」または「表題（リンク）」に対して
    キーワードを部分一致検索し、ヒットした明細をCSVに出力する。
    PDF本文は読まないため、高速。
    """
    targets, label, (d_from, d_to), mode = select_target_folders(root_dir, target_spec)

    print("ルート:", root_dir)
    print("対象指定:", target_spec, "mode=", mode, "from=", d_from, "to=", d_to)
    print("対象日数:", len(targets))
    print("検索キーワード（表題用）:", list(keywords))

    if not targets:
        raise FileNotFoundError("対象期間に該当する日付フォルダが見つかりません。")

    hits = []
    total_rows = 0
    hit_rows = 0

    for idx, d in enumerate(sorted(targets), start=1):
        day_csv = os.path.join(root_dir, d, f"TDnet_Sorted_{d}.csv")
        root_csv = os.path.join(root_dir, f"TDnet_Sorted_{d}.csv")
        csv_path = day_csv if os.path.exists(day_csv) else root_csv if os.path.exists(root_csv) else None

        if csv_path is None:
            print(f"⚠ TDnet_Sorted_{d}.csv が見つかりません（スキップ）")
            continue

        print(f"[{idx}/{len(targets)}] 日付 {d} のCSVを処理中... ({csv_path})")

        df = pd.read_csv(csv_path, dtype=str).fillna("")
        df.columns = [str(c).strip().replace("\ufeff", "") for c in df.columns]

        # 表題テキストを取得（あれば「表題」、なければ「表題（リンク）」から表示テキストを抽出）
        has_plain_title = "表題" in df.columns
        has_link_title = "表題（リンク）" in df.columns

        if not (has_plain_title or has_link_title):
            print(f"⚠ {csv_path} に 表題 / 表題（リンク） 列がありません（スキップ）")
            continue

        for _, r in df.iterrows():
            total_rows += 1

            # 表題（リンク）の元データを取得
            title_link_tdnet = str(r.get("表題（リンク）", "")).strip()

            if has_plain_title:
                title_text = str(r.get("表題", "")).strip()
            else:
                raw = title_link_tdnet
                # =HYPERLINK("URL","表示テキスト") 形式から表示テキストだけ抽出
                m = re.match(r'=HYPERLINK\(".*?",\s*"([^"]*)"\)', raw)
                title_text = m.group(1) if m else raw

            if not title_text:
                continue

            # いずれかのキーワードが部分一致すればヒット
            if not any(kw in title_text for kw in keywords):
                continue

            hit_rows += 1

            # ローカルPDFへのリンクを生成
            pdf_filename = str(r.get("PDFファイル名", "")).strip()
            display_text = title_text or pdf_filename
            local_pdf_path = os.path.join(root_dir, d, pdf_filename)
            title_link_local = f'=HYPERLINK("{local_pdf_path}", "{display_text}")'

            hits.append(
                {
                    "日付": d,
                    "時刻": str(r.get("時刻", "")).strip(),
                    "コード": str(r.get("コード", "")).strip()[:4],
                    "会社名": str(r.get("会社名", "")).strip(),
                    "表題": title_text,
                    "表題（リンク_TDnet）": title_link_tdnet,
                    "表題（リンク_ローカル）": title_link_local,
                    "分類": str(r.get("分類", "")).strip(),
                    "PDFファイル名": pdf_filename,
                    "URL（生）": str(r.get("URL（生）", "")).strip(),
                }
            )

    out_csv = f"{TITLE_SEARCH_CSV_PREFIX}_{label}.csv"
    out_path = os.path.join(root_dir, out_csv)

    if not hits:
        print("表題にヒットする行はありませんでした。")
    else:
        out_df = pd.DataFrame(hits)
        out_df = out_df[
            [
                "日付",
                "時刻",
                "コード",
                "会社名",
                "表題",
                "表題（リンク_TDnet）",
                "表題（リンク_ローカル）",
                "分類",
                "PDFファイル名",
                "URL（生）",
            ]
        ]
        archive_if_exists(out_path)
        out_df.to_csv(out_path, index=False, encoding="utf-8-sig")

    print("\n✅ 表題検索 完了")
    print("総行数:", total_rows)
    print("ヒット行数:", hit_rows)
    print("出力CSV:", out_csv)
    print("保存先:", root_dir)


def run_analyze(root_dir: str, target_spec: str, keywords):
    if fitz is None:
        raise RuntimeError(f"PyMuPDF(fitz)のimportに失敗しました。先に `pip install pymupdf` を実行してください: {_FITZ_IMPORT_ERROR}")

    targets, label, (d_from, d_to), mode = select_target_folders(root_dir, target_spec)

    print("ルート:", root_dir)
    print("対象指定:", target_spec, "mode=", mode, "from=", d_from, "to=", d_to)
    print("対象フォルダ数:", len(targets))
    print("検索キーワード:", list(keywords))

    if not targets:
        raise FileNotFoundError("対象期間に該当する日付フォルダが見つかりません。")

    results = []
    total_pdfs = 0
    hit_files = 0
    processed_pdfs = 0

    # 事前に総PDF数を数えておき、進捗表示に利用する
    folder_pdf_counts = {}
    for d in targets:
        day_dir = os.path.join(root_dir, d)
        pdf_files = [f for f in os.listdir(day_dir) if f.lower().endswith(".pdf")]
        count = len(pdf_files)
        folder_pdf_counts[d] = count
        total_pdfs += count

    print("総PDF数（推定）:", total_pdfs)

    for idx, d in enumerate(targets, start=1):
        day_dir = os.path.join(root_dir, d)
        pdf_files = [f for f in os.listdir(day_dir) if f.lower().endswith(".pdf")]

        print(f"[{idx}/{len(targets)}] 日付フォルダ {d} を処理中... (このフォルダ内PDF数: {len(pdf_files)})")

        folder_hits = 0

        for pdf_name in sorted(pdf_files):
            pdf_path = os.path.join(day_dir, pdf_name)
            processed_pdfs += 1

            kw_pages_dict = extract_hits_pages_from_pdf(
                pdf_path, keywords, pages_sep=PAGES_SEPARATOR
            )

            # いずれかのキーワードがヒットしたか判定
            has_any_hit = any(v for v in kw_pages_dict.values())

            if has_any_hit:
                hit_files += 1
                folder_hits += 1
                code = extract_code_from_pdf_filename(pdf_name)

                row = {
                    "日付": d,
                    "コード": code,
                    "PDFファイル名": pdf_name,
                }
                # キーワードごとの列を追加（ページ番号 or 空文字）
                for kw in keywords:
                    row[kw] = kw_pages_dict.get(kw, "")

                results.append(row)

            # 50件ごとにざっくり進捗を表示（ヒットの有無に関係なく）
            if processed_pdfs % 50 == 0 or processed_pdfs == total_pdfs:
                print(f"  進捗: {processed_pdfs}/{total_pdfs} 件のPDFを解析済み")

        # フォルダ単位のヒット件数を表示
        print(f"  → 日付フォルダ {d} のヒットPDF数: {folder_hits}")

    out_csv = f"{ANALYSIS_CSV_PREFIX}_{label}.csv"
    out_path = os.path.join(root_dir, out_csv)

    df = pd.DataFrame(results)

    # ヒット列数（キーワード列のうち値があるものの数）でソート用の列を一時追加
    if df.empty:
        df_sorted = df
    else:
        df["_hit_kw_count"] = df[keywords].apply(lambda r: sum(1 for v in r if v), axis=1)
        df_sorted = df.sort_values(by=["日付", "_hit_kw_count", "PDFファイル名"], ascending=[False, False, True])
        df_sorted = df_sorted.drop(columns=["_hit_kw_count"])

    # 検索に使用したキーワード一覧（全行同じ値）を列として追加
    if keywords:
        keywords_summary = " / ".join(keywords)
    else:
        keywords_summary = ""

    cols = ["日付", "コード", "PDFファイル名"] + list(keywords)
    if df_sorted.empty:
        df_sorted = pd.DataFrame(columns=cols)
    else:
        df_sorted = df_sorted[cols]
    df_sorted["検索キーワード一覧"] = keywords_summary

    archive_if_exists(out_path)
    df_sorted.to_csv(out_path, index=False, encoding="utf-8-sig")

    print("\n✅ ②A 完了（解析専用・キーワード別ページ列）")
    print("解析PDF数:", total_pdfs)
    print("ヒットPDF数:", hit_files)
    print("出力CSV:", out_csv)
    print("保存先:", root_dir)


def run_distribute(root_dir: str, target_spec: str, stop_on_empty_meta: bool = True, use_local_link: bool = False):
    _, _, label, _ = parse_target_spec(target_spec)

    analysis_csv = f"{ANALYSIS_CSV_PREFIX}_{label}.csv"
    analysis_path = os.path.join(root_dir, analysis_csv)

    if not os.path.exists(analysis_path):
        raise FileNotFoundError(f"②Aの結果が見つかりません: {analysis_path}")

    hits_df = pd.read_csv(analysis_path, dtype=str).fillna("")
    hits_df.columns = [str(c).strip().replace("\ufeff", "") for c in hits_df.columns]

    # 必須列チェック
    required_in_hits = ["日付", "PDFファイル名"]
    for c in required_in_hits:
        if c not in hits_df.columns:
            raise ValueError(f"②A結果に必要な列がありません: {c}")

    # キーワード列を特定（固定列以外がキーワード列）
    fixed_cols = {"日付", "コード", "PDFファイル名", "検索キーワード一覧"}
    keyword_cols = [c for c in hits_df.columns if c not in fixed_cols]

    dates = hits_df["日付"].astype(str).str.strip().tolist()
    tdnet_index, missing_csv_dates = build_tdnet_index_for_dates(root_dir, dates)

    if missing_csv_dates:
        print("⚠ ①CSVが見つからない日付:", ", ".join(missing_csv_dates))

    results = []
    unmatched = 0
    alerts = 0

    for _, r in hits_df.iterrows():
        d = r["日付"].strip()
        pdf_raw = r["PDFファイル名"]
        pdf_key = norm_key(pdf_raw)

        meta = tdnet_index.get((d, pdf_key))
        if not meta:
            unmatched += 1
            continue

        empty = find_empty_fields(meta, REQUIRED_META_FIELDS)
        if empty:
            alerts += 1
            print(f"⚠ 必須項目空欄: {d} / {pdf_raw} -> {empty}")
            if stop_on_empty_meta:
                raise RuntimeError("必須項目が空欄のため処理中断")

        # TDnet側の表示テキストを抽出（会社名 or HYPERLINKの表示テキスト or PDFファイル名）
        title_link_tdnet = meta.get("表題（リンク）", "")
        display_text = meta.get("会社名", "") or pdf_raw
        m = re.match(r'=HYPERLINK\("[^"]*",\s*"([^"]*)"\)', str(title_link_tdnet))
        if m:
            display_text = m.group(1)

        # ローカルPDFへのリンク式
        local_pdf_path = os.path.join(root_dir, d, pdf_raw)
        title_link_local = f'=HYPERLINK("{local_pdf_path}", "{display_text}")'

        row = {
            "日付": d,
            "コード": meta["コード"],
            "会社名": meta["会社名"],
            "分類": meta["分類"],
            "表題（リンク_TDnet）": title_link_tdnet,
            "表題（リンク_ローカル）": title_link_local,
        }
        # キーワード別ページ列をそのまま引き継ぐ
        for kw_col in keyword_cols:
            row[kw_col] = r.get(kw_col, "")

        row["URL（生）"] = meta["URL（生）"]
        results.append(row)

    # 出力ファイル名: 通常版(_sh) と 自分用ローカルリンク版(_local_sh) を分ける
    suffix = "_local_sh.csv" if use_local_link else "_sh.csv"
    out_csv = f"{DISTRIBUTION_CSV_PREFIX}_{label}{suffix}"
    out_path = os.path.join(root_dir, out_csv)

    archive_if_exists(out_path)
    # 0件でもヘッダ付きCSVを出す（Excelで扱いやすくする）
    out_df = pd.DataFrame(results)

    # カラム順: 識別列 → 分類 → 表題リンク → キーワード列 → URL
    cols_order = [
        "日付",
        "コード",
        "会社名",
        "分類",
        "表題（リンク_TDnet）",
        "表題（リンク_ローカル）",
    ] + keyword_cols + [
        "URL（生）",
    ]
    if out_df.empty:
        out_df = pd.DataFrame(columns=cols_order)
    else:
        final_cols = [c for c in cols_order if c in out_df.columns]
        out_df = out_df[final_cols]
    out_df.to_csv(out_path, index=False, encoding="utf-8-sig")

    print("\n✅ ②B 完了（配布用CSV作成・キーワード別ページ列）")
    print("出力:", out_csv)
    print(f"キーワード列: {keyword_cols}")
    print("突合除外件数:", unmatched)
    print("空欄アラート件数:", alerts)


def parse_args():
    p = argparse.ArgumentParser(description="② フリーワード検索（analyze/distribute/title）")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_an = sub.add_parser("analyze", help="②A: PDF全文検索（TDnetアクセスなし）")
    p_an.add_argument("--save-root", default=DEFAULT_SAVE_ROOT, help="保存先ルート（①の出力先）")
    p_an.add_argument("--target", default=DEFAULT_TARGET_SPEC, help="YYYYMMDD / YYYYMM / 'YYYYMMDD YYYYMMDD'")
    p_an.add_argument("--keywords", nargs="+", default=DEFAULT_SEARCH_KEYWORDS, help="検索キーワード（複数指定可）")

    p_di = sub.add_parser("distribute", help="②B: ②A結果と①のCSVを突合して配布用CSVを作成")
    p_di.add_argument("--save-root", default=DEFAULT_SAVE_ROOT, help="保存先ルート（①の出力先）")
    p_di.add_argument("--target", default=DEFAULT_TARGET_SPEC, help="②Aと同じTARGET_SPEC（label一致用）")
    p_di.add_argument("--stop-on-empty-meta", action="store_true", default=True, help="必須メタが空欄ならエラーで停止（既定: 停止）")
    p_di.add_argument("--no-stop-on-empty-meta", dest="stop_on_empty_meta", action="store_false", help="必須メタが空欄でも継続")
    p_di.add_argument(
        "--local-link",
        action="store_true",
        help="（互換性のため残存・現在は無効）",
    )

    p_title = sub.add_parser("title", help="表題（タイトル）に対するキーワード検索（PDF本文は読まない高速版）")
    p_title.add_argument("--save-root", default=DEFAULT_SAVE_ROOT, help="保存先ルート（①の出力先）")
    p_title.add_argument("--target", default=DEFAULT_TARGET_SPEC, help="YYYYMMDD / YYYYMM / 'YYYYMMDD YYYYMMDD'")
    p_title.add_argument(
        "--keywords",
        nargs="+",
        required=True,
        help="表題に含まれていてほしいキーワード（部分一致・複数指定可）",
    )

    return p.parse_args()


def main():
    args = parse_args()
    root_dir = str(Path(args.save_root))

    if args.cmd == "analyze":
        run_analyze(root_dir=root_dir, target_spec=args.target, keywords=args.keywords)
    elif args.cmd == "distribute":
        run_distribute(
            root_dir=root_dir,
            target_spec=args.target,
            stop_on_empty_meta=args.stop_on_empty_meta,
            use_local_link=getattr(args, "local_link", False),
        )
    elif args.cmd == "title":
        run_title_search(root_dir=root_dir, target_spec=args.target, keywords=args.keywords)
    else:
        raise ValueError("不明なコマンドです。")


if __name__ == "__main__":
    main()