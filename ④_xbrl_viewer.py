# -*- coding: utf-8 -*-
"""
XBRL Viewer - browser-based analysis file viewer

Features:
  - Browse XBRL analysis Excel files in browser
  - Click company name to view Excel data in browser
  - Sort by date or code, filter by text/date

Requirements:
  pip install flask openpyxl
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
from flask import Flask, send_file, jsonify, request

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# ============================================================
# 設定
# ============================================================

DEFAULT_DATA_ROOT = os.path.join(os.path.expanduser("~"), "Desktop", "XBRL_Data")
DEFAULT_PORT = 5000

# ============================================================
# ファイルスキャン
# ============================================================

def scan_xbrl_files(data_root: str) -> list:
    root = Path(data_root)
    if not root.exists():
        print(f"  data dir not found: {data_root}")
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
        if not day_dir.is_dir():
            continue
        dir_name = day_dir.name
        if not re.fullmatch(r'\d{8}', dir_name):
            continue

        date_str = dir_name

        for xlsx_file in sorted(day_dir.glob("XBRL*_*.xlsx")):
            fname = xlsx_file.stem
            match = re.match(r'XBRL[^_]*_([^_]+)_(.+)', fname)
            if not match:
                continue

            code = match.group(1)
            company = match.group(2)

            file_key = str(xlsx_file)
            file_mtime = xlsx_file.stat().st_mtime

            if file_key in cache and cache[file_key].get('mtime') == file_mtime:
                title = cache[file_key].get('title', '')
            else:
                title = _read_title_from_excel(xlsx_file)
                cache[file_key] = {'mtime': file_mtime, 'title': title}
                cache_updated = True

            entries.append({
                'date': date_str,
                'date_display': f"{date_str[:4]}/{date_str[4:6]}/{date_str[6:]}",
                'code': code,
                'company': company,
                'title': title,
                'path': str(xlsx_file),
                'filename': xlsx_file.name,
            })

    if cache_updated:
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    print(f"  {len(entries)} files found")
    return entries


def _read_title_from_excel(xlsx_path) -> str:
    try:
        from openpyxl import load_workbook
        wb = load_workbook(str(xlsx_path), read_only=True, data_only=True)
        ws = wb[wb.sheetnames[0]]
        title = ws.cell(row=3, column=2).value or ''
        wb.close()
        return str(title)
    except Exception:
        return ''


def read_excel_as_json(xlsx_path: str) -> dict:
    """Excel ファイルの全シートを JSON 形式で読み取る"""
    from openpyxl import load_workbook
    from openpyxl.styles import PatternFill

    wb = load_workbook(xlsx_path, read_only=False, data_only=True)
    result = {"sheets": []}

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows_data = []

        for row in ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=ws.max_column):
            row_cells = []
            for cell in row:
                val = cell.value
                if val is None:
                    val = ""
                elif isinstance(val, float):
                    if val == int(val) and abs(val) < 1e15:
                        val = int(val)

                # セルの背景色を取得（ハイライト用）
                bg = ""
                try:
                    fill = cell.fill
                    if fill and fill.start_color and fill.start_color.rgb:
                        rgb = str(fill.start_color.rgb)
                        if rgb and rgb != '00000000' and len(rgb) >= 6:
                            bg = rgb[-6:]
                except Exception:
                    pass

                # ヘッダー判定（太字 + 白文字）
                is_header = False
                try:
                    if cell.font and cell.font.bold and cell.font.color:
                        fc = str(cell.font.color.rgb or '')
                        if 'FFFFFF' in fc.upper():
                            is_header = True
                except Exception:
                    pass

                row_cells.append({
                    "v": str(val),
                    "bg": bg,
                    "h": is_header,
                })
            rows_data.append(row_cells)

        result["sheets"].append({
            "name": sheet_name,
            "rows": rows_data,
        })

    wb.close()
    return result


# ============================================================
# HTML テンプレート
# ============================================================

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>XBRL Financial Viewer</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    font-family: 'Segoe UI', 'Yu Gothic UI', 'Meiryo', sans-serif;
    background: #1a1a2e;
    color: #e0e0e0;
    min-height: 100vh;
  }

  /* === ヘッダー === */
  .header {
    background: linear-gradient(135deg, #16213e 0%, #0f3460 100%);
    padding: 18px 32px;
    border-bottom: 2px solid #e94560;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .header h1 { font-size: 20px; font-weight: 600; color: #fff; letter-spacing: 1px; }
  .header .stats { color: #8899aa; font-size: 14px; }

  /* === ツールバー === */
  .toolbar {
    background: #16213e;
    padding: 10px 32px;
    display: flex;
    align-items: center;
    gap: 14px;
    border-bottom: 1px solid #2a2a4a;
    flex-wrap: wrap;
  }
  .toolbar label { color: #8899aa; font-size: 13px; }
  .toolbar select, .toolbar input {
    background: #1a1a2e; color: #e0e0e0;
    border: 1px solid #3a3a5a; border-radius: 4px;
    padding: 5px 10px; font-size: 13px; outline: none;
  }
  .toolbar select:focus, .toolbar input:focus { border-color: #e94560; }
  .toolbar input[type="text"] { width: 220px; }

  /* === 一覧テーブル === */
  .container { padding: 0 32px 32px; }

  table.main-table { width: 100%; border-collapse: collapse; }
  table.main-table thead { position: sticky; top: 0; z-index: 10; }
  table.main-table thead th {
    background: #0f3460; color: #fff; padding: 11px 14px;
    text-align: left; font-weight: 600; font-size: 13px;
    cursor: pointer; user-select: none; white-space: nowrap;
    border-bottom: 2px solid #e94560;
  }
  table.main-table thead th:hover { background: #1a4a80; }
  table.main-table thead th.sort-active { color: #e94560; }
  table.main-table thead th .arrow { margin-left: 4px; font-size: 11px; }
  table.main-table tbody tr { border-bottom: 1px solid #2a2a4a; transition: background 0.12s; cursor: pointer; }
  table.main-table tbody tr:hover { background: #1e2a4a; }
  table.main-table tbody td { padding: 9px 14px; font-size: 13px; }
  .col-date { width: 100px; color: #8899aa; font-variant-numeric: tabular-nums; }
  .col-code { width: 70px; font-weight: 600; font-variant-numeric: tabular-nums; }
  .col-company { width: 180px; }
  .col-company a { color: #53b8f0; text-decoration: none; font-weight: 500; }
  .col-company a:hover { color: #e94560; text-decoration: underline; }
  .col-title { color: #b0b0c0; font-size: 12px; }
  .empty-state { text-align: center; padding: 60px; color: #555; font-size: 15px; }

  /* === 詳細オーバーレイ === */
  .overlay {
    display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
    background: rgba(0,0,0,0.7); z-index: 100;
  }
  .overlay.active { display: flex; justify-content: center; align-items: flex-start; padding-top: 30px; }

  .detail-panel {
    background: #1a1a2e; border: 1px solid #3a3a5a; border-radius: 8px;
    width: 94%; max-width: 1200px; max-height: calc(100vh - 60px);
    display: flex; flex-direction: column; overflow: hidden;
    box-shadow: 0 8px 32px rgba(0,0,0,0.6);
  }

  .detail-header {
    background: linear-gradient(135deg, #16213e, #0f3460);
    padding: 16px 24px; border-bottom: 2px solid #e94560;
    display: flex; justify-content: space-between; align-items: center;
    flex-shrink: 0;
  }
  .detail-header .info h2 { font-size: 18px; color: #fff; margin-bottom: 4px; }
  .detail-header .info p { font-size: 12px; color: #8899aa; }
  .detail-header .actions { display: flex; gap: 8px; }
  .detail-header .actions button, .detail-header .actions a {
    padding: 7px 16px; border-radius: 4px; font-size: 13px;
    cursor: pointer; border: none; text-decoration: none;
  }
  .btn-close { background: #e94560; color: #fff; }
  .btn-close:hover { background: #d03050; }
  .btn-download { background: #2a5a8a; color: #fff; }
  .btn-download:hover { background: #3a6a9a; }

  /* タブ */
  .detail-tabs {
    display: flex; background: #16213e; border-bottom: 1px solid #2a2a4a;
    flex-shrink: 0; overflow-x: auto;
  }
  .detail-tabs button {
    padding: 10px 20px; background: transparent; border: none;
    color: #8899aa; font-size: 13px; cursor: pointer;
    border-bottom: 2px solid transparent; white-space: nowrap;
  }
  .detail-tabs button:hover { color: #e0e0e0; background: #1a2a4a; }
  .detail-tabs button.active {
    color: #53b8f0; border-bottom-color: #53b8f0; background: #1a2244;
  }

  /* シート内容 */
  .detail-body { overflow: auto; flex: 1; padding: 0; }
  .sheet-content { display: none; }
  .sheet-content.active { display: block; }

  table.sheet-table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
  table.sheet-table th {
    background: #0f3460; color: #fff; padding: 8px 12px;
    text-align: left; font-weight: 600; position: sticky; top: 0;
    border-bottom: 1px solid #4472C4;
  }
  table.sheet-table td {
    padding: 6px 12px; border-bottom: 1px solid #2a2a3a;
    white-space: nowrap; max-width: 400px; overflow: hidden; text-overflow: ellipsis;
  }
  table.sheet-table tr:hover td { background: #1e2a4a; }

  .cell-alert { background: rgba(255,180,180,0.12) !important; color: #ff9090; }
  .cell-warn  { background: rgba(255,255,180,0.10) !important; color: #dddd80; }
  .cell-good  { background: rgba(180,255,180,0.10) !important; color: #80dd80; }
  .cell-header { background: #0f3460 !important; color: #fff; font-weight: 600; }
  .cell-number { text-align: right; font-variant-numeric: tabular-nums; }

  .loading { text-align: center; padding: 40px; color: #666; font-size: 14px; }

  .footer { text-align: center; padding: 14px; color: #444; font-size: 11px; }
</style>
</head>
<body>

<div class="header">
  <h1>XBRL Financial Viewer</h1>
  <div class="stats" id="stats"></div>
</div>

<div class="toolbar">
  <label>ソート:</label>
  <select id="sortSelect">
    <option value="date-desc">日付（新しい順）</option>
    <option value="date-asc">日付（古い順）</option>
    <option value="code-asc">コード（昇順）</option>
    <option value="code-desc">コード（降順）</option>
  </select>
  <label>フィルタ:</label>
  <input type="text" id="filterInput" placeholder="会社名・コード・表題で検索...">
  <label>日付:</label>
  <select id="dateFilter"><option value="">すべて</option></select>
</div>

<div class="container">
  <table class="main-table">
    <thead>
      <tr>
        <th class="col-date" data-sort="date">日付 <span class="arrow"></span></th>
        <th class="col-code" data-sort="code">コード <span class="arrow"></span></th>
        <th class="col-company">会社名</th>
        <th class="col-title">表題</th>
      </tr>
    </thead>
    <tbody id="tableBody"></tbody>
  </table>
  <div class="empty-state" id="emptyState" style="display:none;">該当するデータがありません</div>
</div>

<!-- 詳細オーバーレイ -->
<div class="overlay" id="overlay">
  <div class="detail-panel">
    <div class="detail-header">
      <div class="info">
        <h2 id="detailTitle">-</h2>
        <p id="detailSub">-</p>
      </div>
      <div class="actions">
        <a class="btn-download" id="detailDownload" href="#">Excel DL</a>
        <button class="btn-close" id="detailClose">閉じる</button>
      </div>
    </div>
    <div class="detail-tabs" id="detailTabs"></div>
    <div class="detail-body" id="detailBody">
      <div class="loading">読み込み中...</div>
    </div>
  </div>
</div>

<div class="footer">XBRL Financial Viewer</div>

<script>
let allData = [];
let currentSort = 'date-desc';
let currentFilter = '';
let currentDateFilter = '';

/* --- データ読み込み --- */
async function loadData() {
  const res = await fetch('/api/files');
  allData = await res.json();
  populateDateFilter();
  renderTable();
}

function populateDateFilter() {
  const dates = [...new Set(allData.map(d => d.date))].sort().reverse();
  const sel = document.getElementById('dateFilter');
  dates.forEach(d => {
    const opt = document.createElement('option');
    opt.value = d;
    opt.textContent = d.slice(0,4)+'/'+d.slice(4,6)+'/'+d.slice(6);
    sel.appendChild(opt);
  });
}

/* --- フィルタ・ソート --- */
function getFilteredSorted() {
  let data = [...allData];
  if (currentDateFilter) data = data.filter(d => d.date === currentDateFilter);
  if (currentFilter) {
    const q = currentFilter.toLowerCase();
    data = data.filter(d =>
      d.company.toLowerCase().includes(q) ||
      d.code.toLowerCase().includes(q) ||
      d.title.toLowerCase().includes(q)
    );
  }
  const [key, dir] = currentSort.split('-');
  data.sort((a, b) => {
    let va = a[key], vb = b[key];
    if (key === 'code') { const na=parseInt(va),nb=parseInt(vb); if(!isNaN(na)&&!isNaN(nb)){va=na;vb=nb;} }
    if (va < vb) return dir==='asc'?-1:1;
    if (va > vb) return dir==='asc'?1:-1;
    if (key==='date') return a.code<b.code?-1:1;
    return a.date>b.date?-1:1;
  });
  return data;
}

/* --- テーブル描画 --- */
function renderTable() {
  const data = getFilteredSorted();
  const tbody = document.getElementById('tableBody');
  const empty = document.getElementById('emptyState');
  document.getElementById('stats').textContent = data.length+' / '+allData.length+' 件';

  if (!data.length) { tbody.innerHTML=''; empty.style.display='block'; return; }
  empty.style.display='none';

  const frag = document.createDocumentFragment();
  data.forEach(item => {
    const tr = document.createElement('tr');
    const tdD = document.createElement('td'); tdD.className='col-date'; tdD.textContent=item.date_display;
    const tdC = document.createElement('td'); tdC.className='col-code'; tdC.textContent=item.code;
    const tdN = document.createElement('td'); tdN.className='col-company';
    const a = document.createElement('a'); a.href='#'; a.textContent=item.company;
    a.onclick = e => { e.preventDefault(); openDetail(item); };
    tdN.appendChild(a);
    const tdT = document.createElement('td'); tdT.className='col-title'; tdT.textContent=item.title;
    tr.appendChild(tdD); tr.appendChild(tdC); tr.appendChild(tdN); tr.appendChild(tdT);
    frag.appendChild(tr);
  });
  tbody.innerHTML=''; tbody.appendChild(frag);

  document.querySelectorAll('thead th[data-sort]').forEach(th => {
    const arr = th.querySelector('.arrow');
    const [k,d] = currentSort.split('-');
    if(th.dataset.sort===k){th.classList.add('sort-active');arr.textContent=d==='asc'?'▲':'▼';}
    else{th.classList.remove('sort-active');arr.textContent='';}
  });
}

/* --- 詳細表示 --- */
async function openDetail(item) {
  const overlay = document.getElementById('overlay');
  const tabs = document.getElementById('detailTabs');
  const body = document.getElementById('detailBody');

  document.getElementById('detailTitle').textContent = item.code + ' ' + item.company;
  document.getElementById('detailSub').textContent = item.date_display + ' | ' + item.title;
  document.getElementById('detailDownload').href = '/download?path=' + encodeURIComponent(item.path);

  tabs.innerHTML = '';
  body.innerHTML = '<div class="loading">読み込み中...</div>';
  overlay.classList.add('active');

  try {
    const res = await fetch('/api/view?path=' + encodeURIComponent(item.path));
    const data = await res.json();

    tabs.innerHTML = '';
    body.innerHTML = '';

    data.sheets.forEach((sheet, idx) => {
      // タブ
      const btn = document.createElement('button');
      btn.textContent = sheet.name;
      btn.className = idx === 0 ? 'active' : '';
      btn.onclick = () => switchTab(idx);
      tabs.appendChild(btn);

      // シート内容
      const div = document.createElement('div');
      div.className = 'sheet-content' + (idx === 0 ? ' active' : '');
      div.id = 'sheet-' + idx;
      div.appendChild(buildSheetTable(sheet));
      body.appendChild(div);
    });
  } catch(e) {
    body.innerHTML = '<div class="loading">読み込みエラー: '+e.message+'</div>';
  }
}

function switchTab(idx) {
  document.querySelectorAll('.detail-tabs button').forEach((b,i) => b.className = i===idx?'active':'');
  document.querySelectorAll('.sheet-content').forEach((d,i) => d.className = 'sheet-content'+(i===idx?' active':''));
}

function buildSheetTable(sheet) {
  const table = document.createElement('table');
  table.className = 'sheet-table';

  sheet.rows.forEach((row, ri) => {
    const tr = document.createElement('tr');
    const isHeaderRow = row.some(c => c.h);

    row.forEach(cell => {
      const td = document.createElement(isHeaderRow ? 'th' : 'td');
      td.textContent = cell.v;

      // 数値の書式
      if (!isHeaderRow && cell.v && /^-?[\d,]+(\.\d+)?%?$/.test(cell.v.trim())) {
        td.className = 'cell-number';
        // カンマ付き数値に変換
        const num = parseFloat(cell.v.replace(/,/g, '').replace('%',''));
        if (!isNaN(num) && cell.v.includes('%')) {
          // パーセンテージ表示のまま
        } else if (!isNaN(num) && Math.abs(num) >= 1000) {
          td.textContent = num.toLocaleString('ja-JP');
        }
      }

      // 背景色ハイライト
      if (cell.bg) {
        const bg = cell.bg.toUpperCase();
        if (bg === 'FFE0E0' || bg.includes('FFE0')) td.classList.add('cell-alert');
        else if (bg === 'FFFFD0' || bg.includes('FFF')) td.classList.add('cell-warn');
        else if (bg === 'E0FFE0' || bg.includes('E0FF')) td.classList.add('cell-good');
        else if (bg === '4472C4' || bg.includes('3460')) td.classList.add('cell-header');
      }
      if (cell.h) td.classList.add('cell-header');

      tr.appendChild(td);
    });
    table.appendChild(tr);
  });
  return table;
}

function closeDetail() {
  document.getElementById('overlay').classList.remove('active');
}

/* --- イベント --- */
document.getElementById('sortSelect').addEventListener('change', e => { currentSort=e.target.value; renderTable(); });
document.getElementById('filterInput').addEventListener('input', e => { currentFilter=e.target.value; renderTable(); });
document.getElementById('dateFilter').addEventListener('change', e => { currentDateFilter=e.target.value; renderTable(); });
document.getElementById('detailClose').addEventListener('click', closeDetail);
document.getElementById('overlay').addEventListener('click', e => { if(e.target===e.currentTarget) closeDetail(); });
document.addEventListener('keydown', e => { if(e.key==='Escape') closeDetail(); });

document.querySelectorAll('thead th[data-sort]').forEach(th => {
  th.addEventListener('click', () => {
    const key=th.dataset.sort, [ck,cd]=currentSort.split('-');
    currentSort = ck===key ? key+'-'+(cd==='asc'?'desc':'asc') : key+'-asc';
    document.getElementById('sortSelect').value=currentSort;
    renderTable();
  });
});

loadData();
</script>
</body>
</html>"""


# ============================================================
# Flask アプリケーション
# ============================================================

app = Flask(__name__)
file_entries = []


@app.route('/')
def index():
    return HTML_TEMPLATE


@app.route('/api/files')
def api_files():
    return jsonify(file_entries)


@app.route('/api/view')
def api_view():
    """Excel ファイルの中身を JSON で返す（ブラウザ内表示用）"""
    path = request.args.get('path', '')
    if not path or not os.path.isfile(path):
        return jsonify({"error": "file not found"}), 404

    abs_path = os.path.abspath(path)
    if not abs_path.startswith(os.path.abspath(app.config['DATA_ROOT'])):
        return jsonify({"error": "access denied"}), 403

    try:
        data = read_excel_as_json(abs_path)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/download')
def download():
    path = request.args.get('path', '')
    if not path or not os.path.isfile(path):
        return "file not found", 404

    abs_path = os.path.abspath(path)
    if not abs_path.startswith(os.path.abspath(app.config['DATA_ROOT'])):
        return "access denied", 403

    return send_file(abs_path, as_attachment=True, download_name=os.path.basename(abs_path))


# ============================================================
# メイン
# ============================================================

def parse_args():
    p = argparse.ArgumentParser(description="XBRL Viewer")
    p.add_argument("--data-root", default=DEFAULT_DATA_ROOT, help="XBRL data directory")
    p.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port")
    p.add_argument("--host", default="127.0.0.1", help="Host")
    return p.parse_args()


def main():
    global file_entries
    args = parse_args()
    app.config['DATA_ROOT'] = args.data_root

    print("=" * 50)
    print("  XBRL Financial Viewer")
    print("=" * 50)
    print(f"  Data: {args.data_root}")

    file_entries = scan_xbrl_files(args.data_root)

    if not file_entries:
        print("  No files found.")
        return

    url = f"http://{args.host}:{args.port}"
    print(f"  URL:  {url}")
    print(f"  Stop: Ctrl+C")
    print()

    import webbrowser
    webbrowser.open(url)
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
