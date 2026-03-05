# -*- coding: utf-8 -*-
"""
TDnet PDFキーワード検索 Webアプリ (Streamlit)

起動方法:
  streamlit run keyword_search_app.py

検索モード:
  A) ローカルPDF直読み -- PCのPDFを直接スキャン（遅いが確実）
  B) ローカルJSON     -- ⑥で事前抽出したJSONで高速検索
  C) クラウド         -- GitHub PagesのJSONで検索（一般公開用）

PDFの閲覧（全モード共通で各行に「開く」リンク）:
  ローカル → localhost経由でブラウザ表示（期間無制限）
  クラウド → TDnetリンクでブラウザ表示（約30日）
"""

import os
import re
import json
import socket
import threading
import datetime
from bisect import bisect_left
import unicodedata
from http.server import HTTPServer, SimpleHTTPRequestHandler
from functools import partial
from urllib.parse import quote

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

try:
    import yfinance as yf
except ImportError:
    yf = None

# ============================================================
# 設定
# ============================================================
DEFAULT_PDF_ROOT = r"G:\マイドライブ\TDnet_Downloads"
DEFAULT_TEXT_JSON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "text_data")
GITHUB_PAGES_TEXT_BASE = "https://onokazu777.github.io/tdnet-viewer/data/text"
PRIORITY_KEYWORDS = ["事業計画", "予想の修正", "決算短信", "説明資料", "月次", "資本コストや株価"]


# ============================================================
# ローカルPDF配信サーバー
# ============================================================
class _SilentHandler(SimpleHTTPRequestHandler):
    """ログ出力を抑制したHTTPハンドラー"""
    def log_message(self, format, *args):
        pass  # 標準出力にログを出さない


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("localhost", 0))
        return s.getsockname()[1]


def start_local_pdf_server(root_dir: str) -> int:
    """ローカルPDFを配信するHTTPサーバーを起動し、ポート番号を返す"""
    if "pdf_server_port" in st.session_state:
        return st.session_state["pdf_server_port"]

    port = _find_free_port()
    handler = partial(_SilentHandler, directory=root_dir)
    server = HTTPServer(("localhost", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    st.session_state["pdf_server_port"] = port
    return port


def local_pdf_url(port: int, date_str: str, pdf_filename: str) -> str:
    """ローカルPDFのHTTP URL を構築"""
    return f"http://localhost:{port}/{quote(date_str)}/{quote(pdf_filename)}"


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


def normalize_stock_code(code: str) -> str:
    s = norm_key(code).upper().replace(".0", "")
    return s if re.fullmatch(r"[0-9A-Z]{4}", s) else ""


@st.cache_data(ttl=21600, show_spinner=False)
def fetch_daily_closes_from_yahoo(code: str, min_date: str, max_date: str) -> list[tuple[str, float]]:
    """指定銘柄の終値リスト [(YYYYMMDD, close), ...] を返す。"""
    if yf is None:
        return []
    norm_code = normalize_stock_code(code)
    if not norm_code:
        return []
    ticker = f"{norm_code}.T"
    start_dt = datetime.datetime.strptime(min_date, "%Y%m%d").date() - datetime.timedelta(days=7)
    end_dt = datetime.datetime.strptime(max_date, "%Y%m%d").date() + datetime.timedelta(days=45)
    try:
        hist = yf.download(
            ticker,
            start=start_dt.isoformat(),
            end=end_dt.isoformat(),
            interval="1d",
            progress=False,
            auto_adjust=False,
        )
    except Exception:
        return []
    if hist is None or hist.empty:
        return []
    close_col = "Adj Close"
    close_series = None
    if isinstance(hist.columns, pd.MultiIndex):
        if (close_col, ticker) in hist.columns:
            close_series = hist[(close_col, ticker)]
        elif ("Close", ticker) in hist.columns:
            close_series = hist[("Close", ticker)]
        elif close_col in hist.columns.get_level_values(0):
            tmp = hist.xs(close_col, axis=1, level=0)
            close_series = tmp.iloc[:, 0] if isinstance(tmp, pd.DataFrame) else tmp
        elif "Close" in hist.columns.get_level_values(0):
            tmp = hist.xs("Close", axis=1, level=0)
            close_series = tmp.iloc[:, 0] if isinstance(tmp, pd.DataFrame) else tmp
    else:
        if close_col in hist.columns:
            close_series = hist[close_col]
        elif "Close" in hist.columns:
            close_series = hist["Close"]
    if close_series is None:
        return []
    close_series = close_series.dropna()
    if close_series.empty:
        return []
    out = []
    for idx, val in close_series.items():
        # yfinanceの返却型差異対策: DatetimeIndex以外でも日付文字列へ正規化する
        dt = pd.to_datetime(idx, errors="coerce")
        if pd.isna(dt):
            continue
        out.append((dt.strftime("%Y%m%d"), float(val)))
    return out


@st.cache_data(ttl=21600, show_spinner=False)
def fetch_daily_closes_batch_from_yahoo(
    codes: tuple[str, ...], min_date: str, max_date: str
) -> dict[str, list[tuple[str, float]]]:
    """複数銘柄の終値を一括取得して返す。keyは正規化後コード。"""
    if yf is None:
        return {}
    norm_codes = []
    for c in codes:
        n = normalize_stock_code(c)
        if n and n not in norm_codes:
            norm_codes.append(n)
    if not norm_codes:
        return {}
    if len(norm_codes) == 1:
        c = norm_codes[0]
        return {c: fetch_daily_closes_from_yahoo(c, min_date, max_date)}

    ticker_by_code = {c: f"{c}.T" for c in norm_codes}
    start_dt = datetime.datetime.strptime(min_date, "%Y%m%d").date() - datetime.timedelta(days=7)
    end_dt = datetime.datetime.strptime(max_date, "%Y%m%d").date() + datetime.timedelta(days=45)
    try:
        hist = yf.download(
            " ".join(ticker_by_code.values()),
            start=start_dt.isoformat(),
            end=end_dt.isoformat(),
            interval="1d",
            progress=False,
            auto_adjust=False,
            threads=True,
        )
    except Exception:
        return {}
    if hist is None or hist.empty:
        return {}

    out: dict[str, list[tuple[str, float]]] = {}
    for code, ticker in ticker_by_code.items():
        close_series = None
        if isinstance(hist.columns, pd.MultiIndex):
            if ("Adj Close", ticker) in hist.columns:
                close_series = hist[("Adj Close", ticker)]
            elif ("Close", ticker) in hist.columns:
                close_series = hist[("Close", ticker)]
        if close_series is None:
            # 返却形式が単一銘柄/単一列だった場合の後方互換
            if "Adj Close" in hist.columns:
                close_series = hist["Adj Close"]
            elif "Close" in hist.columns:
                close_series = hist["Close"]
        if close_series is None:
            out[code] = []
            continue
        close_series = close_series.dropna()
        rows = []
        for idx, val in close_series.items():
            dt = pd.to_datetime(idx, errors="coerce")
            if pd.isna(dt):
                continue
            rows.append((dt.strftime("%Y%m%d"), float(val)))
        out[code] = rows
    return out


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_shares_outstanding_from_yahoo(code: str) -> float | None:
    """発行済株式数を返す。取得不可時はNone。"""
    if yf is None:
        return None
    norm_code = normalize_stock_code(code)
    if not norm_code:
        return None
    ticker = f"{norm_code}.T"
    value = None
    try:
        info = yf.Ticker(ticker).get_info()
        value = info.get("sharesOutstanding")
    except Exception:
        value = None
    if not value:
        try:
            finfo = yf.Ticker(ticker).fast_info
            value = finfo.get("shares") or finfo.get("shares_outstanding")
        except Exception:
            value = None
    try:
        f = float(value)
        return f if f > 0 else None
    except Exception:
        return None


def calc_forward_returns(df: pd.DataFrame, offsets: list[int], add_market_cap: bool = False) -> pd.DataFrame:
    """検索結果DataFrameにN営業日後騰落率(%)と発表日時価総額(億円)を追加して返す。"""
    if df.empty or "コード" not in df.columns or "日付" not in df.columns:
        return df
    out = df.copy()
    for n in offsets:
        out[f"{n}営業日騰落率(%)"] = ""
    if add_market_cap:
        out["発表日時価総額(億円)"] = ""

    unique_dates = [d for d in out["日付"].astype(str).tolist() if re.fullmatch(r"\d{8}", d)]
    if not unique_dates:
        return out
    min_date = min(unique_dates)
    max_date = max(unique_dates)

    codes_raw = out["コード"].astype(str).tolist()
    codes_norm = sorted(set(normalize_stock_code(c) for c in codes_raw if normalize_stock_code(c)))
    closes_by_code = fetch_daily_closes_batch_from_yahoo(tuple(codes_norm), min_date, max_date)

    code_series_norm = out["コード"].astype(str).map(normalize_stock_code)
    for norm_code in codes_norm:
        if not norm_code:
            continue
        closes = closes_by_code.get(norm_code, [])
        if not closes:
            continue
        shares_outstanding = fetch_shares_outstanding_from_yahoo(norm_code) if add_market_cap else None
        trading_dates = [d for d, _ in closes]
        prices = [p for _, p in closes]
        target_rows = out.index[code_series_norm == norm_code].tolist()
        for row_idx in target_rows:
            ann_date = str(out.at[row_idx, "日付"])
            pos = bisect_left(trading_dates, ann_date)
            if pos >= len(trading_dates):
                continue
            base_price = prices[pos]
            if base_price <= 0:
                continue
            if add_market_cap and shares_outstanding:
                market_cap_oku = (base_price * shares_outstanding) / 1e8
                out.at[row_idx, "発表日時価総額(億円)"] = f"{market_cap_oku:,.2f}"
            for n in offsets:
                if pos + n >= len(prices):
                    continue
                target_price = prices[pos + n]
                ret = (target_price - base_price) / base_price * 100.0
                out.at[row_idx, f"{n}営業日騰落率(%)"] = f"{ret:.2f}"
    return out


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
    root_path: str, date_from: str, date_to: str, keywords: list[str],
    pdf_server_port: int = 0, progress_callback=None,
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

            if any(v for v in kw_result.values()):
                code = extract_code_from_pdf_filename(pdf_name)
                pdf_key = norm_key(pdf_name)
                meta = meta_index.get(pdf_key, {})
                pdf_url = local_pdf_url(pdf_server_port, d, pdf_name) if pdf_server_port else ""
                tdnet_url = meta.get("URL", "")  # TDnetリンク（CSV出力用）
                row = {
                    "日付": d, "コード": code,
                    "企業名": meta.get("会社名", ""),
                    "分類": meta.get("分類", "その他"),
                    "PDF": pdf_url,
                    "ローカルパス": pdf_path,
                    "TDnet_URL": tdnet_url,
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
    available_dates: list[str], load_func,
    pdf_server_port: int = 0,
    pdf_root: str = "",
    progress_callback=None,
) -> pd.DataFrame:
    """JSON経由キーワード検索。pdf_server_port > 0 ならローカルURL、0ならTDnet URL。"""
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
                pdf_name = file_info.get("pdf", "")
                tdnet_url = file_info.get("url", "")  # TDnetリンク（常に保持）
                if pdf_server_port and pdf_name:
                    pdf_url = local_pdf_url(pdf_server_port, d, pdf_name)
                    local_path = os.path.join(pdf_root, d, pdf_name) if pdf_root else ""
                else:
                    pdf_url = tdnet_url  # クラウドモード: TDnet URLを表示用に使う
                    local_path = ""
                row = {
                    "日付": d,
                    "コード": file_info.get("code", ""),
                    "企業名": file_info.get("company", ""),
                    "分類": file_info.get("category", "その他"),
                    "PDF": pdf_url,
                    "ローカルパス": local_path,
                    "TDnet_URL": tdnet_url,
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

    # ----- デプロイモード判定 -----
    # 環境変数 TDNET_DEPLOY_MODE=cloud → 一般公開用（クラウドのみ）
    # 未設定 or local → 個人用（ローカルPDF / ローカルJSON）
    deploy_mode = os.environ.get("TDNET_DEPLOY_MODE", "local")

    # ----- サイドバー -----
    with st.sidebar:
        st.header("検索条件")

        if deploy_mode == "cloud":
            data_source = "クラウド（一般公開用）"
            st.info("クラウドデータで検索します")
        else:
            data_source = st.radio(
                "データソース",
                options=[
                    "ローカルPDF（直接検索）",
                    "ローカルJSON（高速検索）",
                ],
                index=1,
                help=(
                    "ローカルPDF: PCのPDFを直接検索（遅いが確実）\n"
                    "ローカルJSON: ⑥で事前抽出したテキストで高速検索"
                ),
            )
        is_local_pdf = "ローカルPDF" in data_source
        is_local_json = "ローカルJSON" in data_source
        is_cloud = "クラウド" in data_source
        is_local = is_local_pdf or is_local_json

        pdf_root = ""
        text_json_dir = DEFAULT_TEXT_JSON_DIR

        if is_local_pdf:
            pdf_root = st.text_input("PDFフォルダパス", value=DEFAULT_PDF_ROOT)
            available_dates = list_date_folders(pdf_root)
            if not available_dates:
                st.warning(f"PDFフォルダが見つかりません: {pdf_root}")
                st.stop()
        elif is_local_json:
            pdf_root = st.text_input("PDFフォルダパス", value=DEFAULT_PDF_ROOT)
            text_json_dir = st.text_input("テキストJSONフォルダ", value=DEFAULT_TEXT_JSON_DIR)
            available_dates = list_text_json_dates_local(text_json_dir)
            if not available_dates:
                st.warning(f"テキストJSONが見つかりません: {text_json_dir}\n\n⑥を先に実行してください。")
                st.stop()
        else:
            with st.spinner("利用可能な日付を確認中..."):
                available_dates = fetch_text_index_remote()
            if not available_dates:
                st.warning("クラウドにテキストデータが見つかりません。\n\nGitHub Actions → Run workflow を実行してください。")
                st.stop()

        st.info(f"利用可能: {available_dates[0]} 〜 {available_dates[-1]}（{len(available_dates)}日分）")

        min_date = datetime.datetime.strptime(available_dates[0], "%Y%m%d").date()
        max_date = datetime.datetime.strptime(available_dates[-1], "%Y%m%d").date()
        col1, col2 = st.columns(2)
        with col1:
            date_from = st.date_input("開始日", value=max_date, min_value=min_date, max_value=max_date)
        with col2:
            date_to = st.date_input("終了日", value=max_date, min_value=min_date, max_value=max_date)

        st.divider()
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
        add_price_returns = st.checkbox(
            "株価騰落率を計算（5営業日後/20営業日後）",
            value=False,
            help="Yahoo Financeの終値を使って、発表日基準の騰落率を算出します。",
        )
        add_market_cap_only = st.checkbox(
            "発表日時価総額を追加（単独表示）",
            value=False,
            help="発表日以降の最初の取引日終値 × 発行済株式数（Yahoo Finance）で算出します。",
        )
        add_market_cap = add_price_returns or add_market_cap_only
        if add_price_returns:
            st.caption("※ 騰落率を計算する場合、発表日時価総額も自動で表示します。")
        if (add_price_returns or add_market_cap_only) and yf is None:
            st.warning("yfinance が未インストールです。`pip install yfinance` を実行してください。")

        st.divider()
        search_clicked = st.button("検索開始", type="primary", use_container_width=True)
        if keywords_input:
            st.caption(f"キーワード: {', '.join(keywords_input)}")
        else:
            st.warning("キーワードを1つ以上入力してください。")

    # ----- ローカルPDF配信サーバー起動 -----
    pdf_server_port = 0
    if is_local and pdf_root:
        pdf_server_port = start_local_pdf_server(pdf_root)

    # ----- メインエリア: 検索実行 -----
    if search_clicked and keywords_input:
        d_from = date_from.strftime("%Y%m%d")
        d_to = date_to.strftime("%Y%m%d")
        if d_from > d_to:
            st.error("開始日は終了日以前にしてください。")
            st.stop()

        progress_bar = st.progress(0, text="検索中...")

        if is_local_pdf:
            if fitz is None:
                st.error("PyMuPDF がインストールされていません。`pip install pymupdf`")
                st.stop()
            def cb(c, t): progress_bar.progress(c / t if t else 0, text=f"PDF検索中... ({c}/{t})")
            df = search_pdfs_local(pdf_root, d_from, d_to, keywords_input,
                                   pdf_server_port=pdf_server_port, progress_callback=cb)
        elif is_local_json:
            def cb(c, t): progress_bar.progress(c / t if t else 0, text=f"テキスト検索中... ({c}/{t}日)")
            df = search_text_json(
                d_from, d_to, keywords_input, available_dates,
                load_func=lambda d: load_text_json_local(text_json_dir, d),
                pdf_server_port=pdf_server_port, pdf_root=pdf_root, progress_callback=cb,
            )
        else:
            def cb(c, t): progress_bar.progress(c / t if t else 0, text=f"クラウド読み込み中... ({c}/{t}日)")
            df = search_text_json(
                d_from, d_to, keywords_input, available_dates,
                load_func=load_text_json_remote,
                pdf_server_port=0,  # クラウドはTDnet URL
                progress_callback=cb,
            )

        progress_bar.empty()
        if (add_price_returns or add_market_cap) and not df.empty and yf is not None:
            spinner_text = "株価騰落率・時価総額を計算中..." if add_price_returns else "発表日時価総額を計算中..."
            with st.spinner(spinner_text):
                offsets = [5, 20] if add_price_returns else []
                df = calc_forward_returns(df, offsets=offsets, add_market_cap=add_market_cap)
        st.session_state["search_results"] = df
        st.session_state["search_keywords"] = keywords_input
        st.session_state["add_price_returns"] = add_price_returns
        st.session_state["add_market_cap"] = add_market_cap

    # ----- メインエリア: 結果表示（全モード共通） -----
    df = st.session_state.get("search_results")
    keywords_display = st.session_state.get("search_keywords", [])
    add_price_returns = st.session_state.get("add_price_returns", False)
    add_market_cap = st.session_state.get("add_market_cap", False)

    if df is not None:
        if df.empty:
            st.info("ヒットするPDFはありませんでした。")
        else:
            st.subheader("検索結果")

            # 分類フィルタ
            all_categories = sorted(df["分類"].unique().tolist())
            selected_categories = st.multiselect(
                "分類でフィルタ", options=all_categories, default=all_categories,
            )
            filtered_df = df[df["分類"].isin(selected_categories)] if selected_categories else df
            st.metric("ヒット数", f"{len(filtered_df)} 件 / 全 {len(df)} 件")

            # CSVダウンロード（一番上）- BOM付きUTF-8でExcel対応
            csv_export = filtered_df.copy()
            # CSV用の日付フォーマット
            csv_export["日付"] = csv_export["日付"].apply(
                lambda x: f"{x[:4]}/{x[4:6]}/{x[6:]}" if len(str(x)) == 8 else x
            )
            # CSV用: ExcelのHYPERLINK関数でクリック可能なリンクにする
            # ローカルモード → ローカルファイルパス、クラウドモード → TDnet URL
            def _make_hyperlink(row):
                tdnet_url = row.get("TDnet_URL", "")
                local_path = row.get("ローカルパス", "")
                if is_local:
                    # ローカルPDF/ローカルJSON → ローカルファイルのリンク
                    if local_path:
                        return f'=HYPERLINK("{local_path}","開く")'
                else:
                    # クラウド → TDnetリンク
                    if tdnet_url and tdnet_url.startswith("http"):
                        return f'=HYPERLINK("{tdnet_url}","開く")'
                return ""
            csv_export["PDF"] = csv_export.apply(_make_hyperlink, axis=1)
            ret_cols = []
            if add_price_returns:
                ret_cols = [c for c in ["5営業日騰落率(%)", "20営業日騰落率(%)"] if c in csv_export.columns]
            mcap_cols = ["発表日時価総額(億円)"] if add_market_cap and "発表日時価総額(億円)" in csv_export.columns else []
            csv_cols = ["日付", "コード", "企業名", "分類", "PDF"] + keywords_display + ret_cols + mcap_cols
            csv_export = csv_export[[c for c in csv_cols if c in csv_export.columns]]
            # BOM付きUTF-8でバイト列として生成
            csv_bytes = csv_export.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="結果をCSVダウンロード", data=csv_bytes,
                file_name=f"keyword_search_{date_from.strftime('%Y%m%d')}_{date_to.strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )

            # 表示用DataFrame（全モード共通）
            display_df = filtered_df.copy().reset_index(drop=True)
            display_df["日付"] = display_df["日付"].apply(
                lambda x: f"{x[:4]}/{x[4:6]}/{x[6:]}" if len(str(x)) == 8 else x
            )

            ret_cols = []
            if add_price_returns:
                ret_cols = [c for c in ["5営業日騰落率(%)", "20営業日騰落率(%)"] if c in display_df.columns]
            mcap_cols = ["発表日時価総額(億円)"] if add_market_cap and "発表日時価総額(億円)" in display_df.columns else []
            table_cols = ["日付", "コード", "企業名", "分類", "PDF"] + keywords_display + ret_cols + mcap_cols
            table_df = display_df[[c for c in table_cols if c in display_df.columns]]

            st.dataframe(
                table_df,
                use_container_width=True,
                hide_index=True,
                height=min(len(table_df) * 40 + 40, 600),
                column_config={
                    "PDF": st.column_config.LinkColumn(
                        "PDF",
                        display_text="開く",
                    ),
                },
            )

            if is_cloud:
                st.caption("※ TDnetのPDFリンクは公開から約30日で無効になります。")

    elif df is None:
        st.info("左のサイドバーでキーワードと期間を設定し、「検索開始」ボタンを押してください。")


if __name__ == "__main__":
    main()
