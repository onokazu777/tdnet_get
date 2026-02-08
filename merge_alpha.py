"""Merge: viewer's full data + local new data (with alpha code stock data)"""
import json

viewer_path = r"C:\Users\onok\Desktop\tdnet-viewer\data\index.json"
with open(viewer_path, 'r', encoding='utf-8') as f:
    viewer = json.load(f)
print(f"Viewer: {len(viewer)} entries")
viewer_map = {e['detail']: e for e in viewer}

local_path = "docs/data/index.json"
with open(local_path, 'r', encoding='utf-8') as f:
    local = json.load(f)
print(f"Local (20260206): {len(local)} entries")
local_map = {e['detail']: e for e in local}

# Merge: update viewer entries with local data (stock + pdf)
updated = 0
for entry in viewer:
    detail = entry['detail']
    if detail in local_map:
        new = local_map[detail]
        for k in ('pbr', 'forward_pe', 'div_yield', 'pdf_url'):
            if k in new and new[k] is not None:
                entry[k] = new[k]
        updated += 1

# Save
with open(viewer_path, 'w', encoding='utf-8') as f:
    json.dump(viewer, f, ensure_ascii=False, indent=2)

# Also update local full copy
with open(local_path, 'w', encoding='utf-8') as f:
    json.dump(viewer, f, ensure_ascii=False, indent=2)

alpha = [e for e in viewer if not e['code'].isdigit() and e.get('pbr') is not None]
print(f"Updated: {updated}, Alpha with PBR: {len(alpha)}, Total: {len(viewer)}")
