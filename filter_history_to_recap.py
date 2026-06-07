#!/usr/bin/env python3
"""
filter_history_to_recap.py — filter history files to only contain slugs present in recap.

Moves history entries whose slugs are NOT in the recap to archive files.

Usage:
  python3 filter_history_to_recap.py                              # dry run
  python3 filter_history_to_recap.py --apply
  python3 filter_history_to_recap.py --apply --include-archived-recap
                                                                   # include archived recap slugs
Options:
  --apply                    actually modify files (default is dry run)
  --include-archived-recap   match against BOTH the working recap AND the .archive.jsonl
                             (keeps 30 markets total instead of just the 13 in current recap)
"""
import json, os, sys, shutil
from datetime import datetime

APPLY = False
INCLUDE_ARCHIVED = False
RECAP_PATH = 'market_recap_history.jsonl'
ARCHIVED_RECAP = 'market_recap_history.archive.jsonl'
TARGETS = ['market_history.jsonl', 'market_history_lite.jsonl']

args = sys.argv[1:]
for a in args:
    if a == '--apply': APPLY = True
    elif a == '--include-archived-recap': INCLUDE_ARCHIVED = True

# Collect slugs present in recap (+ optionally archived recap)
keep_slugs = set()
for path in [RECAP_PATH] + ([ARCHIVED_RECAP] if INCLUDE_ARCHIVED else []):
    if not os.path.exists(path): continue
    with open(path) as f:
        for line in f:
            if not line.strip(): continue
            try: m = json.loads(line)
            except: continue
            slug = m.get('slug', '')
            if 'btc-updown-5m-' in slug:
                keep_slugs.add(slug)

print(f"Mode: {'APPLY' if APPLY else 'DRY RUN'}")
print(f"Include archived recap: {INCLUDE_ARCHIVED}")
print(f"Keep-set: {len(keep_slugs)} slugs from {RECAP_PATH}" +
      (f" + {ARCHIVED_RECAP}" if INCLUDE_ARCHIVED else ""))
print()

for target in TARGETS:
    print(f"━━━ {target} ━━━")
    if not os.path.exists(target):
        print("  (not found)"); continue
    keep_lines = []
    archive_lines = []
    with open(target) as f:
        for line in f:
            if not line.strip(): continue
            try: m = json.loads(line)
            except: archive_lines.append(line); continue
            slug = m.get('slug', '')
            if slug in keep_slugs:
                keep_lines.append(line)
            else:
                archive_lines.append(line)

    print(f"  Current:  {len(keep_lines) + len(archive_lines)} entries")
    print(f"  Would keep:     {len(keep_lines)}")
    print(f"  Would archive:  {len(archive_lines)}")

    if not APPLY:
        print("  (dry run)"); continue

    if not archive_lines:
        print("  ✅ Already filtered"); continue

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    bak = f"{target}.bak.{ts}"
    shutil.copy2(target, bak)
    print(f"  ✓ backup: {bak}")

    archive_path = target.replace('.jsonl', '.noncap_archive.jsonl')
    with open(archive_path, 'a') as f:
        for line in archive_lines:
            f.write(line if line.endswith('\n') else line + '\n')
    print(f"  ✓ appended {len(archive_lines)} to {archive_path}")

    tmp = target + '.tmp'
    with open(tmp, 'w') as f:
        for line in keep_lines:
            f.write(line if line.endswith('\n') else line + '\n')
    os.replace(tmp, target)
    print(f"  ✓ rewrote {target} with {len(keep_lines)} entries")

if not APPLY and any(os.path.exists(t) for t in TARGETS):
    print("\nAdd --apply to actually do it.")
    print("Add --include-archived-recap to match against the 30-slug archive instead of current 13.")
