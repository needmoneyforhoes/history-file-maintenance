#!/usr/bin/env python3
"""
split_history_files.py — move old markets from working jsonl files to archive files.

Creates backups first, splits by slug threshold, and reports what happened.
Safe to re-run (idempotent if archive already exists).

Usage:
  python3 split_history_files.py                      # dry run (shows what would happen)
  python3 split_history_files.py --apply              # actually do it
  python3 split_history_files.py --apply --threshold 1776295500

Files handled (if present):
  market_recap_history.jsonl  → market_recap_history.archive.jsonl
  market_history_lite.jsonl   → market_history_lite.archive.jsonl
  market_history.jsonl        → market_history.archive.jsonl

What it does:
  1. Back up original to .bak (timestamped)
  2. Split entries: slug < threshold → archive, slug >= threshold → new working file
  3. Atomically replace original working file
  4. Show before/after sizes and counts

Safety:
  - Dry run is the default — you must pass --apply to actually modify files
  - Always creates .bak backup before modifying originals
  - If archive file exists, APPENDS to it (doesn't overwrite) — safe to re-run
  - If anything goes wrong mid-process, original .bak is untouched
"""
import json, os, sys, shutil
from datetime import datetime

THRESHOLD = 1776295500  # slugs below this are "old / sparse-era"
APPLY = False

# Parse args
args = sys.argv[1:]
i = 0
while i < len(args):
    if args[i] == '--apply':
        APPLY = True; i += 1
    elif args[i] == '--threshold' and i+1 < len(args):
        THRESHOLD = int(args[i+1]); i += 2
    else:
        print(f"Unknown arg: {args[i]}")
        print(__doc__); sys.exit(1)

FILES = [
    'market_recap_history.jsonl',
    'market_history_lite.jsonl',
    'market_history.jsonl',
]


def get_slug_num(entry):
    """Extract numeric slug from an entry. Returns None if not parseable."""
    slug = entry.get('slug') or entry.get('market_id') or entry.get('id')
    if not isinstance(slug, str): return None
    if 'btc-updown-5m-' not in slug: return None
    try:
        return int(slug.replace('btc-updown-5m-', ''))
    except:
        return None


def process_file(path):
    print(f"\n━━━ {path} ━━━")
    if not os.path.exists(path):
        print("  (file not found, skipping)")
        return None

    # Read all entries
    old_entries, new_entries, unparseable = [], [], []
    with open(path) as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip(): continue
            try:
                m = json.loads(line)
            except:
                unparseable.append((line_num, line[:80]))
                continue
            slug_num = get_slug_num(m)
            if slug_num is None:
                unparseable.append((line_num, f"no_slug: {list(m.keys())[:5]}"))
                continue
            if slug_num < THRESHOLD:
                old_entries.append(line)
            else:
                new_entries.append(line)

    total_size = os.path.getsize(path)
    print(f"  Current: {len(old_entries) + len(new_entries) + len(unparseable):,} lines, "
          f"{total_size:,} bytes")
    print(f"    → would archive (old):    {len(old_entries):,} entries")
    print(f"    → would keep (new):       {len(new_entries):,} entries")
    if unparseable:
        print(f"    ⚠️  unparseable lines:    {len(unparseable)} (will be preserved in .bak only)")
        for ln, excerpt in unparseable[:3]:
            print(f"       line {ln}: {excerpt}")

    if not old_entries:
        print("  ✅ No old entries to archive — file is already clean.")
        return {'archived': 0, 'kept': len(new_entries), 'unparseable': len(unparseable)}

    if not APPLY:
        print("  (dry run — add --apply to actually split)")
        return {'archived': len(old_entries), 'kept': len(new_entries), 'unparseable': len(unparseable)}

    # ─── Actually apply changes ───
    archive_path = path.replace('.jsonl', '.archive.jsonl')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    bak_path = f"{path}.bak.{timestamp}"

    # 1. Back up original
    shutil.copy2(path, bak_path)
    print(f"  ✓ backed up to {bak_path}")

    # 2. Append old entries to archive (not overwrite)
    with open(archive_path, 'a') as f:
        for line in old_entries:
            f.write(line if line.endswith('\n') else line + '\n')
    print(f"  ✓ appended {len(old_entries)} entries to {archive_path}")

    # 3. Rewrite working file with only new entries
    tmp_path = path + '.tmp'
    with open(tmp_path, 'w') as f:
        for line in new_entries:
            f.write(line if line.endswith('\n') else line + '\n')
    os.replace(tmp_path, path)
    print(f"  ✓ rewrote {path} with {len(new_entries)} entries")

    new_size = os.path.getsize(path)
    print(f"  Size: {total_size:,} → {new_size:,} bytes "
          f"({(new_size/total_size*100):.0f}% of original)")

    return {'archived': len(old_entries), 'kept': len(new_entries), 'unparseable': len(unparseable)}


def main():
    print(f"Splitter config:")
    print(f"  Threshold:  slug < {THRESHOLD} goes to archive")
    print(f"  Mode:       {'APPLY (will modify files)' if APPLY else 'DRY RUN (no changes)'}")
    print(f"  Files:      {FILES}")

    totals = {'archived': 0, 'kept': 0, 'unparseable': 0}
    for path in FILES:
        result = process_file(path)
        if result:
            for k in totals: totals[k] += result[k]

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"  Total entries archived:   {totals['archived']:,}")
    print(f"  Total entries kept:       {totals['kept']:,}")
    print(f"  Total unparseable:        {totals['unparseable']:,}")

    if not APPLY and totals['archived'] > 0:
        print(f"\n  This was a DRY RUN. To actually split, run:")
        print(f"    python3 {sys.argv[0]} --apply")
    elif APPLY:
        print(f"\n  ✅ Split complete. Backups saved as *.bak.<timestamp>")
        print(f"  If anything looks wrong, restore with:")
        print(f"    cp <file>.bak.<timestamp> <file>")


if __name__ == '__main__':
    main()
