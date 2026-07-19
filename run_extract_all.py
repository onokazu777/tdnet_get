import sys, os, glob
base = None
for d in glob.glob(r"C:\Users\onok\Desktop\*\tdnet_get"):
    if os.path.isdir(d):
        base = d
        break
if not base:
    print("not found"); sys.exit(1)
os.chdir(base)

extractor = None
for f in os.listdir(base):
    if "pdf_text_extractor" in f and f.endswith(".py"):
        extractor = os.path.join(base, f)
        break

from importlib.machinery import SourceFileLoader
mod = SourceFileLoader("ext", extractor).load_module()

save_root = r"G:\マイドライブ\TDnet_Downloads"
out_dir = os.path.join(base, "text_data")
dates = mod.list_date_folders(save_root)
print(f"Total dates: {len(dates)}")

existing = set()
if os.path.isdir(out_dir):
    import re
    for fn in os.listdir(out_dir):
        m = re.match(r"text_(\d{8})\.json$", fn)
        if m:
            existing.add(m.group(1))

to_extract = [d for d in dates if d not in existing]
print(f"Already extracted: {len(existing)}, To extract: {len(to_extract)}")

for i, d in enumerate(to_extract):
    print(f"\n[{i+1}/{len(to_extract)}] {d}")
    mod.extract_date(save_root, d, out_dir)

print(f"\nDone! Total JSON files: {len(existing) + len(to_extract)}")
