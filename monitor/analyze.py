"""analyze.py - cari "tag" pesan yang paling sering muncul di logs\\_all.log
supaya gampang bikin filter.   python analyze.py [--all]

Default hanya menampilkan pesan yang BELUM masuk channel manapun (kolom '-').
"""
import os
import re
import sys
from collections import Counter, defaultdict

from common import COLOR_CODE, load_ini, log_dir

HERE = os.path.dirname(os.path.abspath(__file__))
ini = open(os.path.join(HERE, "ini_path.txt"), encoding="utf-8").read().strip()
path = os.path.join(log_dir(load_ini(ini), ini), "_all.log")
show_all = "--all" in sys.argv

# tag = "(Xxx)" | "[Xxx]" | "Word:" at the start of the line
TAG = re.compile(r"^\s*(\([^)]{1,30}\)|\[[^\]]{1,30}\]|[A-Za-z][\w -]{0,20}:)")

counts, examples, channel_of = Counter(), defaultdict(list), {}
for raw in open(path, encoding="cp1252", errors="replace"):
    p = raw.rstrip("\r\n").split("\t", 4)
    if len(p) < 5:
        continue
    _, _, ch, _, text = p
    if ch != "-" and not show_all:
        continue
    plain = COLOR_CODE.sub("", text).strip()
    if not plain or " says: " in plain or plain.startswith("* "):
        continue  # skip empty lines & normal IC chat
    m = TAG.match(plain)
    tag = m.group(1).strip() if m else "(tanpa tag)"
    counts[tag] += 1
    channel_of[tag] = ch
    if len(examples[tag]) < 2:
        examples[tag].append(plain[:110])

print(f"Sumber: {path}\n")
for tag, n in counts.most_common(40):
    print(f"{n:5}x  {tag:<25} -> channel: {channel_of[tag]}")
    for e in examples[tag]:
        print(f"         contoh: {e}")
print("\nTambahkan ke AdminFilter.ini misalnya:\n  [Channel:nama]\n  StartsWith=<tag>\n")
