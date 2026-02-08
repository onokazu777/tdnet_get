# -*- coding: utf-8 -*-
"""
① TDnetアクセスしてダウンロードする処理（月日付別フォルダ保存）

【Windowsローカル実行版】
- Colab専用の `!pip` / `google.colab` / `/content/drive` 依存を除去
- 保存先をローカル/ドライブパスに対応

実行例:
  python "①_tdnetアクセスしてダウンロードする処理（月日付別フォルダ保存）.py" --target "20260202"
  python "①_tdnetアクセスしてダウンロードする処理（月日付別フォルダ保存）.py" --target "20260105 20260109"
"""

# ============================================================
# ① TDnetアクセスしてダウンロードする処理（範囲指定対応版）※修正版（正規化強化）
#
# できること
# - TDnetの一覧を「日別フォルダ（YYYYMMDD）」に保存しながら、複数日をまとめて回収
# - 対象指定は 3パターン
#   A) 日別: "20260109"
#   B) 月指定: "202601"           （2026年1月）
#   C) 範囲:  "20260105 20260109" （from to）
#
# 保存先（Google Drive）
#   MyDrive/{SAVE_ROOT}/{YYYYMMDD}/
#     ├── *.pdf
#     └── TDnet_Sorted_YYYYMMDD.csv
#   ※日別CSVは同時にルート直下にもコピー保存する
#
# 修正版の主目的（今回の不一致原因への対策）
# - PDFファイル名（会社名・表題など）に含まれる日本語の濁点等は、
#   環境や処理経路（HTML→文字列→保存、OS→ファイル名取得等）により
#   「見た目は同じでも内部文字列が違う（合成/分離）」が起こりうる。
# - これを防ぐため、ファイル名に使う文字列を Unicode NFKC 正規化し、
#   さらに安全なファイル名へ整形して保存する。
#
# 注意
# - PDF本文解析は行わない（②Aで行う想定）
# - PyMuPDFは不要
# - TDnetへのアクセスが日数分増える（ページ数×日数 + PDF本数）
# - 大量に回す場合は PAGE_SLEEP_SEC / PDF_SLEEP_SEC を増やすのが安全
# ============================================================

import os
import datetime
import requests
import pandas as pd
import time
import re
import unicodedata
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import argparse
from pathlib import Path


# -----------------------------
# 設定
# -----------------------------
# 対象指定（以下のいずれか）
# TARGET_SPEC = "20260109"               # 日別
# TARGET_SPEC = "202601"                 # 月指定
# TARGET_SPEC = "20260105 20260109"      # 範囲指定（from to）
DEFAULT_TARGET_SPEC = "20260203"


# 保存先（Windowsローカル）
# 例: G:\マイドライブ\TDnet_Downloads
DEFAULT_SAVE_ROOT = r"G:\マイドライブ\TDnet_Downloads"

# TDnet負荷軽減
PAGE_SLEEP_SEC = 3   # 一覧ページ取得ごとに待機
PDF_SLEEP_SEC = 1    # PDF1本DL成功ごとに待機

# タイトルに含まれたら完全除外（リストにも入れない・PDFも取らない）
# 例：ETF/ETNなど不要な日次開示を排除
EXCLUDE_KEYWORDS = ["ＥＴＦ", "ETF", "ETN", "ＥＴＮ","_MAXIS"]

# 分類（タイトルベース）
# 左ほど優先度が高い（CSVソートに使用）
PRIORITY_KEYWORDS = ["事業計画", "予想の修正", "決算短信", "説明資料", "月次", "資本コストや株価"]

# 既存ファイルがある場合の扱い
# True なら、同名PDFが既にあれば再DLしない（基本はこれで安全）
SKIP_IF_EXISTS = True

# 1日フォルダを事前にクリーンにするか（通常はFalse推奨）
# Trueにすると、その日付フォルダ配下のPDF/CSVを削除してから取り直す
# （残骸混在を絶対に避けたい場合のみ使う）
CLEAN_DAY_FOLDER = False


# -----------------------------
# Unicode正規化（NFKC）
# -----------------------------
def nfkc(s: str) -> str:
    """
    Unicode正規化（NFKC）
    - 全角/半角の揺れ
    - 濁点の合成/分離
    - 一部互換文字
    などを揃える目的。
    """
    return unicodedata.normalize("NFKC", str(s))

# -----------------------------
# 日付指定のパース
# -----------------------------
def parse_target_spec(spec: str):
    """
    入力:
      - "YYYYMMDD"
      - "YYYYMM"
      - "YYYYMMDD YYYYMMDD" （from to）
    出力:
      (from_yyyymmdd, to_yyyymmdd, label, mode)
    """
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
        d1, d2 = parts[0], parts[1]
        if not (re.fullmatch(r"\d{8}", d1) and re.fullmatch(r"\d{8}", d2)):
            raise ValueError("範囲指定は 'YYYYMMDD YYYYMMDD' 形式で指定してください。")
        if d1 > d2:
            d1, d2 = d2, d1
        return d1, d2, f"{d1}_{d2}", "range"

    raise ValueError("TARGET_SPEC の指定が不正です。")


def iter_dates_yyyymmdd(d_from: str, d_to: str):
    """YYYYMMDDの範囲で日付を列挙（両端含む）"""
    start = datetime.datetime.strptime(d_from, "%Y%m%d").date()
    end = datetime.datetime.strptime(d_to, "%Y%m%d").date()
    cur = start
    while cur <= end:
        yield cur.strftime("%Y%m%d")
        cur += datetime.timedelta(days=1)


# -----------------------------
# 分類・除外・ファイル名整形
# -----------------------------
def get_category_score(title: str):
    """
    PRIORITY_KEYWORDS に含まれる最初のキーワードで分類。
    ヒットしない場合は「その他」扱い。
    """
    for i, kw in enumerate(PRIORITY_KEYWORDS):
        if kw in title:
            return i, kw
    return 999, "その他"


def is_excluded(title: str) -> bool:
    """
    EXCLUDE_KEYWORDS がタイトルに含まれる場合は完全除外。
    注意:
    - ここはタイトル文字列側の正規化も行う（全角/半角揺れ対策）
    """
    if not EXCLUDE_KEYWORDS:
        return False
    t = nfkc(title)
    return any(nfkc(k) in t for k in EXCLUDE_KEYWORDS)


def safe_filename(s: str, max_len: int = 120) -> str:
    """
    Drive/Windows/一般ファイルシステムで安全に扱えるようにファイル名を整形する。

    行うこと
    - Unicode NFKC 正規化（濁点合成/分離などを統一）
    - 禁則文字を "_" に置換:  \\ / : * ? " < > |
    - 連続空白を整理（スペース1個に）
    - 前後空白を削除
    - 長すぎる場合は切り詰め
    """
    s = nfkc(s)
    s = re.sub(r'[\\/:*?"<>|]', "_", s)
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > max_len:
        s = s[:max_len].rstrip()
    return s


# -----------------------------
# PDFダウンロード
# -----------------------------
def download_pdf(session: requests.Session, url: str, save_path: str, headers: dict, cookies: dict) -> bool:
    """
    PDFをストリーミングで保存。
    失敗した場合はFalseを返す（例外は握りつぶさずログ表示）。
    """
    try:
        r = session.get(url, headers=headers, cookies=cookies, stream=True, timeout=60)
        r.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)
        return True
    except Exception as e:
        print(f"   ❌ PDFダウンロード失敗: {e}")
        return False


# -----------------------------
# （任意）日付フォルダのクリーンアップ
# -----------------------------
def cleanup_day_folder(day_dir: str):
    """
    その日付フォルダ配下のPDF/CSVを削除する。
    - 残骸混在を絶対に避けたい場合のみ利用
    """
    if not os.path.isdir(day_dir):
        return
    for fn in os.listdir(day_dir):
        p = os.path.join(day_dir, fn)
        if os.path.isfile(p) and (fn.lower().endswith(".pdf") or fn.lower().endswith(".csv")):
            try:
                os.remove(p)
            except Exception:
                pass


# -----------------------------
# 引数
# -----------------------------
def parse_args():
    p = argparse.ArgumentParser(description="TDnet一覧取得＆PDFダウンロード（日付別フォルダ保存）")
    p.add_argument("--target", default=DEFAULT_TARGET_SPEC, help="YYYYMMDD / YYYYMM / 'YYYYMMDD YYYYMMDD'")
    p.add_argument("--save-root", default=DEFAULT_SAVE_ROOT, help="保存先フォルダ（例: G:\\マイドライブ\\TDnet_Downloads）")
    p.add_argument("--page-sleep", type=float, default=PAGE_SLEEP_SEC, help="一覧ページ取得ごとの待機秒")
    p.add_argument("--pdf-sleep", type=float, default=PDF_SLEEP_SEC, help="PDF1本保存ごとの待機秒")
    p.add_argument("--skip-if-exists", action="store_true", default=SKIP_IF_EXISTS, help="同名PDFが既にあれば再DLしない")
    p.add_argument("--no-skip-if-exists", dest="skip_if_exists", action="store_false", help="同名PDFがあっても再DLする")
    p.add_argument("--clean-day-folder", action="store_true", default=CLEAN_DAY_FOLDER, help="日付フォルダのPDF/CSVを削除してから取得")
    return p.parse_args()


# -----------------------------
# メイン：指定範囲を日ごとに処理
# -----------------------------
def main():
    args = parse_args()
    target_spec = args.target
    save_root = Path(args.save_root)
    save_root.mkdir(parents=True, exist_ok=True)

    d_from, d_to, label, mode = parse_target_spec(target_spec)

    print(f"🎯 対象指定: {target_spec}（mode={mode}, from={d_from}, to={d_to}）")
    print(f"📁 保存ルート: {save_root}")

    base_url_template = "https://www.release.tdnet.info/inbs/I_list_{}_{}.html"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://www.release.tdnet.info/index.html",
    }
    cookies = {"cb_agree": "0"}
    session = requests.Session()

    # 全期間の統計
    total_page_access = 0
    total_pdf_success = 0
    total_excluded = 0
    days_with_no_data = []

    for target_date_str in iter_dates_yyyymmdd(d_from, d_to):
        print("\n" + "=" * 60)
        print(f"📅 日付: {target_date_str} を処理します")

        # 日付別フォルダ
        day_dir = save_root / target_date_str
        day_dir.mkdir(parents=True, exist_ok=True)

        # 必要ならクリーンアップ（通常はFalse）
        if args.clean_day_folder:
            print("   🧹 日付フォルダをクリーンアップします（PDF/CSV削除）")
            cleanup_day_folder(str(day_dir))

        data_list = []
        page_num = 1

        day_page_access = 0
        day_pdf_success = 0
        day_excluded = 0

        while True:
            page_str = f"{page_num:03}"
            target_url = base_url_template.format(page_str, target_date_str)

            print(f"   ...Page {page_str} を確認中")
            res = session.get(target_url, headers=headers, cookies=cookies, timeout=60)
            day_page_access += 1
            res.encoding = "utf-8"

            # データ無し判定
            if res.status_code == 404 or "該当するデータはありません" in res.text:
                if page_num == 1:
                    print("   ⚠️ 該当データなし（休日等の可能性）")
                    days_with_no_data.append(target_date_str)
                break

            soup = BeautifulSoup(res.text, "html.parser")
            rows = soup.find_all("tr")

            # TDnet側のHTMLが想定より少ない場合は終了
            if len(rows) < 5:
                break

            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 5:
                    continue

                # 取得文字列は、後段でNFKC正規化して揺れを吸収
                r_time = nfkc(cols[0].get_text(strip=True))
                r_code = nfkc(cols[1].get_text(strip=True))  # 4桁数字とは限らない（例: 137A）
                r_name = nfkc(cols[2].get_text(strip=True))
                r_title = nfkc(cols[3].get_text(strip=True))

                # 除外（完全スキップ：CSVにも入れないしPDFも取らない）
                if is_excluded(r_title):
                    day_excluded += 1
                    continue

                # PDFリンク取得（リンクが取れない行はスキップ）
                link_tag = cols[3].find("a")
                if not link_tag:
                    link_tag = cols[4].find("a")
                if not link_tag:
                    continue

                pdf_link = urljoin(target_url, link_tag.get("href"))

                # 分類
                score, category_name = get_category_score(r_title)

                # PDFファイル名生成
                t = r_time.replace(":", "")
                code4 = (r_code[:4] or "").strip()

                fn = (
                    f"{safe_filename(code4, max_len=4)}_"
                    f"{safe_filename(t, max_len=10)}_"
                    f"{safe_filename(r_name)}_"
                    f"{safe_filename(r_title)}.pdf"
                )
                pdf_path = day_dir / fn

                # PDF保存（既存があればスキップ）
                need_download = True
                if args.skip_if_exists and pdf_path.exists():
                    need_download = False

                if need_download:
                    ok = download_pdf(session, pdf_link, str(pdf_path), headers, cookies)
                    if ok:
                        day_pdf_success += 1
                        print(f"   ✅ 保存: {fn}")
                        if args.pdf_sleep > 0:
                            time.sleep(args.pdf_sleep)

                # 一覧CSV用（除外以外は全件入れる）
                sheet_link = f'=HYPERLINK("{pdf_link}", "{r_title}")'
                data_list.append(
                    {
                        "優先度": score,
                        "分類": category_name,
                        "時刻": r_time,
                        "コード": code4,
                        "会社名": r_name,
                        "表題（リンク）": sheet_link,
                        "URL（生）": pdf_link,
                        "PDFファイル名": fn,
                    }
                )

            page_num += 1
            if args.page_sleep > 0:
                time.sleep(args.page_sleep)

        # 日別CSV保存
        if data_list:
            df = pd.DataFrame(data_list)

            # 優先度（小さいほど優先）→ 時刻（新しい順）で並べる
            df_sorted = df.sort_values(by=["優先度", "時刻"], ascending=[True, False])
            df_final = df_sorted[["分類", "時刻", "コード", "会社名", "表題（リンク）", "URL（生）", "PDFファイル名"]]

            out_csv = f"TDnet_Sorted_{target_date_str}.csv"

            # ① 日付別フォルダに保存
            out_path = day_dir / out_csv
            df_final.to_csv(out_path, index=False, encoding="utf-8-sig")
            print(f"   📝 一覧CSV保存: {out_csv}")

            # ② ルートフォルダにもコピー保存（②Bで参照できるように）
            out_path_root = save_root / out_csv
            df_final.to_csv(out_path_root, index=False, encoding="utf-8-sig")
            print(f"   📝 一覧CSV保存（ルート）: {out_csv}")
        else:
            print("   📝 一覧CSV: （作成なし）")

        # 日別統計
        print(f"   📊 日別統計: page_access={day_page_access}, pdf_success={day_pdf_success}, excluded={day_excluded}")

        # 期間合算
        total_page_access += day_page_access
        total_pdf_success += day_pdf_success
        total_excluded += day_excluded

    print("\n" + "=" * 60)
    print("✅ ①完了（範囲取得）")
    print(f"   期間: {d_from} ～ {d_to} （mode={mode}）")
    print(f"   一覧ページアクセス合計: {total_page_access}")
    print(f"   PDFダウンロード成功合計: {total_pdf_success}")
    print(f"   除外件数合計: {total_excluded}")
    if days_with_no_data:
        print(f"   データなし日: {', '.join(days_with_no_data)}")
    print(f"   保存ルート: {save_root}")


if __name__ == "__main__":
    main()
