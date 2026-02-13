# -*- coding: utf-8 -*-
"""
TDnet PDFキーワード検索 Webアプリ (Streamlit)

起動方法:
  streamlit run keyword_search_app.py

検索モード:
  A) ローカルPDF直読み -- PCのPDFを直接スキャン（遅いが確実）
  B) ローカルJSON     -- ⑥で事前抽出したJSONで高速検索
  C) クラウド         -- GitHub PagesのJSONで検索（一般公開用）

PDFの閲覧:
  全モード共通でTDnetのPDFリンクを表示。クリックでブラウザにPDFが開く。
"""

import os
import re
import json
import datetime
import unicodedata
import pandas as pd
import streamlit as st

try:
    import requests as _requests
except ImportError:
    _requests = None

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

# ============================================================
# 設定
# ============================================================
DEFAULT_PDF_ROOT = r"G:\マイドライブ\TDnet_Downloads"
DEFAULT_TEXT_JSON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "text_data")
GITHUB_PAGES_TEXT_BASE = "https://onokazu777.github.io/tdnet-viewer/data/text"
PRIORITY_KEYWORDS = ["事業計画", "予想の修正", "決算短信", "説明資料", "月次", "資本コストや株価"]


# ============================================================
# ユーティリティ
# ============================================================
def norm_key(s: str) -> str:
    return unicodedata.normalize("NFKC", str(s)).strip()


def get_category(title: str) -> str:
    for kw in PRIORITY_KEYWORDS:
        if kw in title:
            return kw
    return "その他"


def extract_code_from_pdf_filename(pdf_filename: str) -> str:
    m = re.match(r"^([0-9A-Za-z]{4})_", str(pdf_filename))
    return m.group(1).upper() if m else ""


def list_date_folders(root_path: str) -> list[str]:
    if not os.path.isdir(root_path):
        return []
    return sorted([
        d for d in os.listdir(root_path)
        if os.path.isdir(os.path.join(root_path, d)) and re.fullmatch(r"\d{8}", d)
    ])


# ============================================================
# データソース A: ローカルPDF直読み
# ============================================================
def load_tdnet_meta(root_path: str, date_str: str) -> dict:
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
            "会社名": str(r.get("会社名", "")).strip(),
            "コード": str(r.get("コード", "")).strip()[:4],
            "分類": bunrui,
            "表題": display_text,
            "URL": url or str(r.get("URL（生）", "")).strip(),
        }
    return index


def search_pdfs_local(
    root_path: str, date_from: str, date_to: str, keywords: list[str], progress_callback=None,
) -> pd.DataFrame:
    all_dates = list_date_folders(root_path)
    target_dates = [d for d in all_dates if date_from <= d <= date_to]
    if not target_dates:
        return pd.DataFrame()

    total_pdfs = 0
    date_pdfs: dict[str, list[str]] = {}
    for d in target_dates:
        day_dir = os.path.join(root_path, d)
        pdfs = [f for f in os.listdir(day_dir) if f.lower().endswith(".pdf")]
        date_pdfs[d] = pdfs
        total_pdfs += len(pdfs)
    if total_pdfs == 0:
        return pd.DataFrame()

    results = []
    processed = 0
    for d in target_dates:
        day_dir = os.path.join(root_path, d)
        meta_index = load_tdnet_meta(root_path, d)
        for pdf_name in sorted(date_pdfs[d]):
            processed += 1
            pdf_path = os.path.join(day_dir, pdf_name)
            try:
                doc = fitz.open(pdf_path)
                kw_pages = {kw: set() for kw in keywords}
                for page_index, page in enumerate(doc, start=1):
                    text = page.get_text("text")
                    for kw in keywords:
                        if kw in text:
                            kw_pages[kw].add(page_index)
                doc.close()
                kw_result = {kw: " ".join(str(p) for p in sorted(pages)) for kw, pages in kw_pages.items()}
            except Exception:
                kw_result = {kw: "" for kw in keywords}

            has_any_hit = any(v for v in kw_result.values())
            if has_any_hit:
                code = extract_code_from_pdf_filename(pdf_name)
                pdf_key = norm_key(pdf_name)
                meta = meta_index.get(pdf_key, {})
                row = {
                    "日付": d, "コード": code,
                    "企業名": meta.get("会社名", ""),
                    "分類": meta.get("分類", "その他"),
                    "PDF": meta.get("URL", ""),
                }
                for kw in keywords:
                    row[kw] = kw_result.get(kw, "")
                results.append(row)
            if progress_callback:
                progress_callback(processed, total_pdfs)

    return pd.DataFrame(results) if results else pd.DataFrame()


# ============================================================
# データソース B/C: JSON経由検索
# ============================================================
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_text_index_remote() -> list[str]:
    url = f"{GITHUB_PAGES_TEXT_BASE}/index.json"
    try:
        resp = _requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json().get("dates", [])
    except Exception:
        return []


def list_text_json_dates_local(text_dir: str) -> list[str]:
    if not os.path.isdir(text_dir):
        return []
    return sorted([
        m.group(1) for fn in os.listdir(text_dir)
        if (m := re.match(r"text_(\d{8})\.json$", fn))
    ])


@st.cache_data(ttl=600, show_spinner=False)
def load_text_json_remote(date_str: str) -> dict:
    url = f"{GITHUB_PAGES_TEXT_BASE}/text_{date_str}.json"
    try:
        resp = _requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {}


def load_text_json_local(text_dir: str, date_str: str) -> dict:
    path = os.path.join(text_dir, f"text_{date_str}.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def search_text_json(
    date_from: str, date_to: str, keywords: list[str],
    available_dates: list[str], load_func, progress_callback=None,
) -> pd.DataFrame:
    target_dates = [d for d in available_dates if date_from <= d <= date_to]
    if not target_dates:
        return pd.DataFrame()

    results = []
    total_dates = len(target_dates)

    for idx, d in enumerate(target_dates):
        data = load_func(d)
        if not data or "files" not in data:
            if progress_callback:
                progress_callback(idx + 1, total_dates)
            continue

        for file_info in data["files"]:
            pages = file_info.get("pages", [])
            kw_result = {}
            for kw in keywords:
                hit_pages = []
                for page_idx, page_text in enumerate(pages, start=1):
                    if kw in page_text:
                        hit_pages.append(str(page_idx))
                kw_result[kw] = " ".join(hit_pages)

            if any(v for v in kw_result.values()):
                row = {
                    "日付": d,
                    "コード": file_info.get("code", ""),
                    "企業名": file_info.get("company", ""),
                    "分類": file_info.get("category", "その他"),
                    "PDF": file_info.get("url", ""),
                }
                for kw in keywords:
                    row[kw] = kw_result.get(kw, "")
                results.append(row)

        if progress_callback:
            progress_callback(idx + 1, total_dates)

    return pd.DataFrame(results) if results else pd.DataFrame()


# ============================================================
# Streamlit UI
# ============================================================
def main():
    st.set_page_config(page_title="TDnet PDFキーワード検索", page_icon="🔍", layout="wide")

    st.title("TDnet PDFキーワード検索")
    st.caption("TDnet適時開示PDFから、指定キーワードが記述されているページを検索します。")

    # ----- サイドバー -----
    with st.sidebar:
        st.header("検索条件")

        # データソース
        data_source = st.radio(
            "データソース",
            options=[
                "ローカルPDF（直接検索）",
                "ローカルJSON（高速検索）",
                "クラウド（一般公開用）",
            ],
            index=0,
            help=(
                "ローカルPDF: PCのPDFを直接検索（遅いが確実）\n"
                "ローカルJSON: ⑥で事前抽出したテキストで高速検索\n"
                "クラウド: GitHub Pagesのデータで検索（PDF不要）"
            ),
        )

        is_local_pdf = "ローカルPDF" in data_source
        is_local_json = "ローカルJSON" in data_source
        is_cloud = "クラウド" in data_source

        pdf_root = ""
        text_json_dir = DEFAULT_TEXT_JSON_DIR

        if is_local_pdf:
            pdf_root = st.text_input(
                "PDFフォルダパス", value=DEFAULT_PDF_ROOT,
                help="①でダウンロードしたPDFが保存されているフォルダ",
            )
            available_dates = list_date_folders(pdf_root)
            if not available_dates:
                st.warning(f"PDFフォルダが見つかりません: {pdf_root}")
                st.stop()

        elif is_local_json:
            text_json_dir = st.text_input(
                "テキストJSONフォルダ", value=DEFAULT_TEXT_JSON_DIR,
                help="⑥で抽出したテキストJSONのフォルダ",
            )
            available_dates = list_text_json_dates_local(text_json_dir)
            if not available_dates:
                st.warning(
                    f"テキストJSONが見つかりません: {text_json_dir}\n\n"
                    "⑥_pdf_text_extractor.py を先に実行してください。"
                )
                st.stop()

        else:  # is_cloud
            with st.spinner("利用可能な日付を確認中..."):
                available_dates = fetch_text_index_remote()
            if not available_dates:
                st.warning(
                    "クラウドにテキストデータが見つかりません。\n\n"
                    "GitHub Actions の手動実行が必要です:\n"
                    "1. GitHub → tdnet_get → Actions\n"
                    "2. 'Daily XBRL Update' → Run workflow"
                )
                st.stop()

        st.info(f"利用可能: {available_dates[0]} 〜 {available_dates[-1]}（{len(available_dates)}日分）")

        # 期間指定
        min_date = datetime.datetime.strptime(available_dates[0], "%Y%m%d").date()
        max_date = datetime.datetime.strptime(available_dates[-1], "%Y%m%d").date()
        col1, col2 = st.columns(2)
        with col1:
            date_from = st.date_input("開始日", value=max_date, min_value=min_date, max_value=max_date)
        with col2:
            date_to = st.date_input("終了日", value=max_date, min_value=min_date, max_value=max_date)

        st.divider()

        # キーワード入力
        st.subheader("キーワード（最大5個）")
        keywords_input = []
        default_keywords = ["増産", "上方修正", "シェア拡大", "価格改定", "需要回復"]
        for i in range(5):
            kw = st.text_input(
                f"キーワード {i + 1}",
                value=default_keywords[i] if i < len(default_keywords) else "",
                key=f"kw_{i}",
                label_visibility="collapsed" if i > 0 else "visible",
                placeholder=f"キーワード {i + 1}（空欄は無視）",
            )
            if kw.strip():
                keywords_input.append(kw.strip())

        st.divider()
        search_clicked = st.button("検索開始", type="primary", use_container_width=True)

        if keywords_input:
            st.caption(f"キーワード: {', '.join(keywords_input)}")
        else:
            st.warning("キーワードを1つ以上入力してください。")

    # ----- メインエリア -----
    if search_clicked and keywords_input:
        d_from = date_from.strftime("%Y%m%d")
        d_to = date_to.strftime("%Y%m%d")

        if d_from > d_to:
            st.error("開始日は終了日以前にしてください。")
            st.stop()

        st.subheader(f"検索結果: {d_from} 〜 {d_to}")
        progress_bar = st.progress(0, text="検索中...")

        if is_local_pdf:
            if fitz is None:
                st.error("PyMuPDF がインストールされていません。`pip install pymupdf`")
                st.stop()

            def update_progress(current, total):
                progress_bar.progress(current / total if total else 0, text=f"PDF検索中... ({current}/{total})")

            df = search_pdfs_local(pdf_root, d_from, d_to, keywords_input, progress_callback=update_progress)

        elif is_local_json:
            def update_progress(current, total):
                progress_bar.progress(current / total if total else 0, text=f"テキスト検索中... ({current}/{total}日)")

            df = search_text_json(
                d_from, d_to, keywords_input, available_dates,
                load_func=lambda d: load_text_json_local(text_json_dir, d),
                progress_callback=update_progress,
            )
        else:
            def update_progress(current, total):
                progress_bar.progress(current / total if total else 0, text=f"クラウド読み込み中... ({current}/{total}日)")

            df = search_text_json(
                d_from, d_to, keywords_input, available_dates,
                load_func=load_text_json_remote,
                progress_callback=update_progress,
            )

        progress_bar.empty()

        st.session_state["search_results"] = df
        st.session_state["search_keywords"] = keywords_input

    # ----- 結果表示 -----
    df = st.session_state.get("search_results")
    keywords_display = st.session_state.get("search_keywords", [])

    if df is not None:
        if df.empty:
            st.info("ヒットするPDFはありませんでした。")
        else:
            # 分類フィルタ
            all_categories = sorted(df["分類"].unique().tolist())
            selected_categories = st.multiselect(
                "分類でフィルタ", options=all_categories, default=all_categories,
            )
            filtered_df = df[df["分類"].isin(selected_categories)] if selected_categories else df

            st.metric("ヒット数", f"{len(filtered_df)} 件 / 全 {len(df)} 件")

            # 表示用DataFrame
            display_df = filtered_df.copy().reset_index(drop=True)
            display_df["日付"] = display_df["日付"].apply(
                lambda x: f"{x[:4]}/{x[4:6]}/{x[6:]}" if len(str(x)) == 8 else x
            )

            # カラム順: 日付, コード, 企業名, 分類, PDF（TDnetリンク）, キーワード列
            display_cols = ["日付", "コード", "企業名", "分類", "PDF"] + keywords_display
            display_df = display_df[[c for c in display_cols if c in display_df.columns]]

            # テーブル表示（チェックボックスなし、PDFはクリック可能リンク）
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                height=min(len(display_df) * 40 + 40, 600),
                column_config={
                    "PDF": st.column_config.LinkColumn(
                        "PDF",
                        display_text="開く",
                        help="クリックでTDnetのPDFを表示",
                    ),
                },
            )

            st.caption("※ TDnetのPDFリンクは公開から約30日で無効になります。")

            # CSVダウンロード
            csv_data = filtered_df.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label="結果をCSVダウンロード", data=csv_data,
                file_name=f"keyword_search_{d_from}_{d_to}.csv", mime="text/csv",
            )

    elif df is None:
        st.info("左のサイドバーでキーワードと期間を設定し、「検索開始」ボタンを押してください。")


if __name__ == "__main__":
    main()
