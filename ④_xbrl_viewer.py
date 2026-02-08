# -*- coding: utf-8 -*-
"""
XBRL Financial Viewer (Streamlit版)

Usage:
  streamlit run ④_xbrl_viewer.py

環境変数:
  XBRL_DATA_ROOT : データディレクトリ（デフォルト ~/Desktop/XBRL_Data）
"""

import os
import re
import json
import math
import streamlit as st
import pandas as pd
from pathlib import Path

# ============================================================
# ページ設定
# ============================================================

st.set_page_config(
    page_title="XBRL Financial Viewer",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="collapsed",  # サイドバーは管理者ログイン用
)

DATA_ROOT = os.environ.get(
    "XBRL_DATA_ROOT",
    os.path.join(os.path.expanduser("~"), "Desktop", "XBRL_Data"),
)

# ============================================================
# カスタム CSS
# ============================================================

st.markdown("""<style>
    .block-container { padding-top: 0.8rem; padding-bottom: 1rem; }
    .section-hdr { font-size: 0.95rem; font-weight: 700; margin: 0.6rem 0 0.2rem; }
    .note-sm { font-size: 0.75rem; color: #888; margin-bottom: 0.2rem; }
    .pos { color: #51cf66; }
    .neg { color: #ff6b6b; }
</style>""", unsafe_allow_html=True)

# ============================================================
# 管理者認証（サイドバー）
# ============================================================

if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

with st.sidebar:
    st.markdown("#### 管理者ログイン")
    _pwd = st.text_input("パスワード", type="password", label_visibility="collapsed",
                         placeholder="パスワードを入力...")
    if _pwd:
        try:
            correct = st.secrets.get("admin_password", "")
        except Exception:
            correct = ""
        if _pwd == correct:
            st.session_state.is_admin = True
            st.success("認証OK — ダウンロード有効")
        else:
            st.session_state.is_admin = False
            st.error("パスワードが違います")
    if st.session_state.is_admin:
        st.caption("Excel ダウンロードが有効です")
        if st.button("ログアウト"):
            st.session_state.is_admin = False
            st.rerun()


# ============================================================
# 数値フォーマット
# ============================================================

def trunc(v, d=3):
    if not isinstance(v, (int, float)) or math.isnan(v) or math.isinf(v):
        return v
    f = 10 ** d
    return math.floor(v * f) / f if v >= 0 else math.ceil(v * f) / f


def fmt_amount(v):
    if not isinstance(v, (int, float)):
        return str(v) if v not in (None, "") else ""
    if math.isnan(v) or math.isinf(v):
        return ""
    if v == int(v) and abs(v) >= 1_000_000:
        return f"{int(v) // 1_000_000:,}"
    t = trunc(v)
    if t == int(t):
        return f"{int(t):,}"
    return f"{t:,.3f}".rstrip('0').rstrip('.')


def fmt_rate(v):
    if not isinstance(v, (int, float)):
        return str(v) if v not in (None, "") else ""
    if math.isnan(v) or math.isinf(v):
        return ""
    return f"{trunc(v * 100, 1):.1f}%"


def fmt_generic(v):
    if v is None or v == "":
        return ""
    if not isinstance(v, (int, float)):
        return str(v)
    if math.isnan(v) or math.isinf(v):
        return ""
    t = trunc(v)
    if t == int(t):
        return f"{int(t):,}"
    return f"{t:,.3f}".rstrip('0').rstrip('.')


def format_financial_df(df):
    """財務テーブルを表示用に整形"""
    r = df.copy()
    for col in r.columns:
        c = str(col)
        if '増減率' in c:
            r[col] = r[col].apply(lambda x: fmt_rate(x) if isinstance(x, (int, float)) else (str(x) if x else ""))
        elif ('当期' in c or '前期' in c or '増減額' in c) and '（%）' not in c and '（pt）' not in c:
            r[col] = r[col].apply(lambda x: fmt_amount(x) if isinstance(x, (int, float)) else (str(x) if x else ""))
        else:
            r[col] = r[col].apply(lambda x: fmt_generic(x) if isinstance(x, (int, float)) else (str(x) if x is not None else ""))
    return r


def color_num(val):
    """数値セルの色分けスタイル"""
    try:
        s = str(val).replace(',', '').replace('%', '').replace('pt', '').strip()
        if not s or s == '-':
            return ''
        v = float(s)
        if v < 0:
            return 'color: #ff6b6b'
        if v > 0:
            return 'color: #51cf66'
    except (ValueError, TypeError):
        pass
    return ''


# ============================================================
# データ読み込み
# ============================================================

def _read_summary(xlsx_path):
    info = {'title': '', 'op_cur': None, 'op_prev': None, 'op_diff': None}
    try:
        from openpyxl import load_workbook
        wb = load_workbook(str(xlsx_path), read_only=True, data_only=True)
        ws = wb[wb.sheetnames[0]]
        info['title'] = str(ws.cell(row=3, column=2).value or '')
        for row in ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=4):
            if '営業利益率' in str(row[0].value or ''):
                for k, i in [('op_cur', 1), ('op_prev', 2), ('op_diff', 3)]:
                    v = row[i].value
                    info[k] = round(float(v), 2) if v is not None else None
                break
        wb.close()
    except Exception:
        pass
    return info


@st.cache_data(ttl=600, show_spinner="ファイルをスキャン中...")
def scan_files(data_root: str):
    root = Path(data_root)
    if not root.exists():
        return []

    cache_path = root / "_index_cache.json"
    cache = {}
    if cache_path.exists():
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache = json.load(f)
        except Exception:
            cache = {}

    entries = []
    cache_updated = False

    for day_dir in sorted(root.iterdir()):
        if not day_dir.is_dir() or not re.fullmatch(r'\d{8}', day_dir.name):
            continue
        d = day_dir.name
        for xf in sorted(day_dir.glob("XBRL*_*.xlsx")):
            m = re.match(r'XBRL[^_]*_([^_]+)_(.+)', xf.stem)
            if not m:
                continue
            code, company = m.group(1), m.group(2)
            fk = str(xf)
            mt = xf.stat().st_mtime

            if fk in cache and cache[fk].get('mtime') == mt:
                c = cache[fk]
                title, oc, op, od = c.get('title', ''), c.get('op_cur'), c.get('op_prev'), c.get('op_diff')
            else:
                s = _read_summary(xf)
                title, oc, op, od = s['title'], s['op_cur'], s['op_prev'], s['op_diff']
                cache[fk] = {'mtime': mt, 'title': title, 'op_cur': oc, 'op_prev': op, 'op_diff': od}
                cache_updated = True

            # [日本基準](連結) がMarkdownリンクにならないようエスケープ
            safe_title = title.replace('[', '\\[')

            entries.append({
                '日付': f"{d[:4]}/{d[4:6]}/{d[6:]}",
                'コード': code,
                '会社名': company,
                '表題': safe_title,
                '営利 当期%': oc,
                '営利 前期%': op,
                '営利 差分pt': od,
                '_path': fk,
                '_date': d,
            })

    if cache_updated:
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    return entries


@st.cache_data(show_spinner="Excel読み込み中...")
def read_excel_detail(path: str):
    from openpyxl import load_workbook
    wb = load_workbook(path, data_only=True)
    result = {}
    for name in wb.sheetnames:
        ws = wb[name]
        rows = []
        for row in ws.iter_rows(max_row=ws.max_row, max_col=ws.max_column, values_only=True):
            rows.append(list(row))
        result[name] = rows
    wb.close()
    return result


# ============================================================
# 分析サマリーパーサー
# ============================================================

def parse_summary_sections(rows):
    INFO_KEYS = {'会社名', 'コード', '表題', '日付'}
    company_info = {}
    sections = []
    cur_sec = None
    cur_hdr = None
    cur_dat = []

    for row in rows:
        first = str(row[0] or '').strip() if row and row[0] else ''
        if first in INFO_KEYS:
            company_info[first] = row[1] if len(row) > 1 and row[1] else ''
            continue
        if first.startswith('【'):
            if cur_sec and cur_dat:
                sections.append((cur_sec, cur_hdr, cur_dat))
            cur_sec, cur_hdr, cur_dat = first, None, []
            continue
        if cur_sec and cur_hdr is None and any(v for v in row if v is not None and v != ''):
            cur_hdr = [str(v or '') for v in row]
            continue
        if cur_sec and cur_hdr and any(v for v in row if v is not None and v != ''):
            cur_dat.append(row)

    if cur_sec and cur_dat:
        sections.append((cur_sec, cur_hdr, cur_dat))
    return company_info, sections


# ============================================================
# メイン
# ============================================================

def main():
    st.markdown("### XBRL Financial Viewer")

    entries = scan_files(DATA_ROOT)
    if not entries:
        st.warning(f"データが見つかりません: {DATA_ROOT}")
        return

    all_df = pd.DataFrame(entries)

    # ============================================================
    # 上部フィルタバー
    # ============================================================
    c1, c2, c3 = st.columns([1.5, 2.5, 1])
    with c1:
        sort_map = {
            "日付 ↓新しい順": ("_date", False),
            "日付 ↑古い順": ("_date", True),
            "コード ↑昇順": ("コード", True),
            "コード ↓降順": ("コード", False),
            "営利 当期% ↓高い順": ("営利 当期%", False),
            "営利 当期% ↑低い順": ("営利 当期%", True),
            "営利 差分pt ↓高い順": ("営利 差分pt", False),
            "営利 差分pt ↑低い順": ("営利 差分pt", True),
        }
        sort_label = st.selectbox("ソート", list(sort_map.keys()), label_visibility="collapsed")
        sort_col, sort_asc = sort_map[sort_label]
    with c2:
        search = st.text_input("検索", placeholder="会社名・コード・表題で検索...",
                               label_visibility="collapsed")
    with c3:
        dates = sorted(all_df['_date'].unique(), reverse=True)
        date_labels = ["全日付"] + [f"{d[:4]}/{d[4:6]}/{d[6:]}" for d in dates]
        date_vals = [""] + list(dates)
        di = st.selectbox("日付", range(len(date_labels)),
                          format_func=lambda i: date_labels[i], label_visibility="collapsed")
        sel_date = date_vals[di]

    # フィルタ適用
    df = all_df.copy()
    if sel_date:
        df = df[df['_date'] == sel_date]
    if search:
        q = search.lower()
        df = df[
            df['会社名'].str.lower().str.contains(q, na=False) |
            df['コード'].str.lower().str.contains(q, na=False) |
            df['表題'].str.lower().str.contains(q, na=False)
        ]
    df = df.sort_values(sort_col, ascending=sort_asc, na_position='last')

    st.caption(f"{len(df)} / {len(all_df)} 件　※行をクリックすると詳細を表示")

    # ============================================================
    # 一覧テーブル（行選択可能）
    # ============================================================
    disp_cols = ['日付', 'コード', '会社名', '表題',
                 '営利 当期%', '営利 前期%', '営利 差分pt']
    disp_df = df[disp_cols].reset_index(drop=True)

    # 色付きスタイル
    margin_cols = ['営利 当期%', '営利 前期%', '営利 差分pt']
    styled = disp_df.style.map(color_num, subset=margin_cols)

    event = st.dataframe(
        styled,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "日付": st.column_config.TextColumn("日付", width="small"),
            "コード": st.column_config.TextColumn("コード", width="small"),
            "会社名": st.column_config.TextColumn("会社名", width="medium"),
            "表題": st.column_config.TextColumn("表題", width="large"),
            "営利 当期%": st.column_config.NumberColumn("営利 当期%", format="%.2f%%", width="small"),
            "営利 前期%": st.column_config.NumberColumn("営利 前期%", format="%.2f%%", width="small"),
            "営利 差分pt": st.column_config.NumberColumn("営利 差分pt", format="%.2fpt", width="small"),
        },
        height=min(len(disp_df) * 35 + 60, 600),
    )

    # ============================================================
    # 詳細表示（行選択時にインライン表示）
    # ============================================================
    if event and event.selection and event.selection.rows:
        idx = event.selection.rows[0]
        item = df.iloc[idx]
        _show_detail(item)


def _show_detail(item):
    """選択された企業のExcel詳細をインラインで表示"""
    st.divider()
    path = item['_path']

    # ヘッダー
    if st.session_state.get('is_admin'):
        hc1, hc2 = st.columns([6, 1])
    else:
        hc1 = st.container()
        hc2 = None

    with hc1:
        st.markdown(f"#### {item['コード']}　{item['会社名']}")
        st.caption(f"{item['日付']}　|　{item['表題']}")

    if hc2 is not None:
        with hc2:
            try:
                with open(path, 'rb') as f:
                    st.download_button(
                        "Excel DL", f.read(),
                        file_name=os.path.basename(path),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
            except Exception:
                pass

    # Excel読み込み
    sheets = read_excel_detail(path)
    if not sheets:
        st.warning("データなし")
        return

    tabs = st.tabs(list(sheets.keys()))
    for tab, (name, rows) in zip(tabs, sheets.items()):
        with tab:
            if not rows:
                st.info("空のシート")
                continue
            if name == "分析サマリー":
                _render_summary(rows)
            else:
                _render_data_sheet(rows)


def _render_summary(rows):
    company_info, sections = parse_summary_sections(rows)

    if company_info:
        cols = st.columns(min(len(company_info), 4))
        for i, (k, v) in enumerate(company_info.items()):
            cols[i % len(cols)].markdown(
                f"**{k}**<br>{v}", unsafe_allow_html=True)
        st.divider()

    for sec_name, headers, data in sections:
        st.markdown(f"<p class='section-hdr'>{sec_name}</p>", unsafe_allow_html=True)
        if not headers or not data:
            continue

        mx = len(headers)
        padded = [list(r)[:mx] + [None] * max(0, mx - len(r)) for r in data]
        df = pd.DataFrame(padded, columns=headers)

        has_fin = any('増減率' in str(h) or
                      ('当期' in str(h) and '（%）' not in str(h))
                      for h in headers)
        if has_fin:
            df = format_financial_df(df)
            st.markdown("<p class='note-sm'>※ 金額は百万円単位 / 増減率は%表示</p>",
                        unsafe_allow_html=True)

        # 数値列に色付け
        num_cols = [c for c in df.columns if any(k in c for k in ['当期', '前期', '増減', '差分'])]
        if num_cols:
            styled = df.style.map(color_num, subset=num_cols)
            st.dataframe(styled, hide_index=True, use_container_width=True)
        else:
            st.dataframe(df, hide_index=True, use_container_width=True)


def _render_data_sheet(rows):
    if len(rows) < 2:
        st.dataframe(pd.DataFrame(rows), hide_index=True)
        return

    headers = [str(v or f'列{i+1}') for i, v in enumerate(rows[0])]
    mx = len(headers)
    data = []
    for r in rows[1:]:
        if all(v is None or v == '' for v in r):
            continue
        data.append(list(r)[:mx] + [None] * max(0, mx - len(r)))

    if not data:
        st.info("データなし")
        return

    df = pd.DataFrame(data, columns=headers)
    has_fin = any('増減率' in str(h) or
                  ('当期' in str(h) and '（%）' not in str(h))
                  for h in headers)
    if has_fin:
        df = format_financial_df(df)
        st.markdown("<p class='note-sm'>※ 金額は百万円単位 / 増減率は%表示</p>",
                    unsafe_allow_html=True)

    num_cols = [c for c in df.columns if any(k in c for k in ['当期', '前期', '増減', '差分'])]
    if num_cols:
        styled = df.style.map(color_num, subset=num_cols)
        st.dataframe(styled, hide_index=True, use_container_width=True,
                     height=min(len(df) * 35 + 60, 600))
    else:
        st.dataframe(df, hide_index=True, use_container_width=True,
                     height=min(len(df) * 35 + 60, 600))


if __name__ == "__main__":
    main()
