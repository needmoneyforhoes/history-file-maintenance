#!/usr/bin/env python3
"""
split_recap_by_quality.py — split market_recap_history.jsonl based on REPLAY quality.

Unlike split_history_files.py (which uses slug-threshold), this script inspects
each recap entry's corresponding replay file and moves entries to archive if the
replay failed the quality filter (sparse ticks, late first_cd, big gaps).

Usage:
  python3 split_recap_by_quality.py                    # dry run
  python3 split_recap_by_quality.py --apply            # do it
  python3 split_recap_by_quality.py --replays /path/to/replay_dir --recap /path/to/recap.jsonl

Quality requirements (must all pass):
  - replay file exists
  - ≥1500 ticks
  - first_cd ≥ 285 (started within 15s of market open)
  - max tick gap ≤ 10s

Outputs:
  market_recap_history.jsonl          — only premium-quality entries
  market_recap_history.archive.jsonl  — entries whose replays failed quality
"""
import json, os, sys, glob, shutil
from datetime import datetime

APPLY = False
RECAP_PATH = 'market_recap_history.jsonl'
REPLAY_DIR = '.'
MIN_TICKS = 1500
MAX_FIRST_CD_SKIP = 15
MAX_TICK_GAP = 10

args = sys.argv[1:]
i = 0
while i < len(args):
    if args[i] == '--apply': APPLY = True; i += 1
    elif args[i] == '--recap' and i+1 < len(args): RECAP_PATH = args[i+1]; i += 2
    elif args[i] == '--replays' and i+1 < len(args): REPLAY_DIR = args[i+1]; i += 2
    else: print(f"Unknown arg: {args[i]}"); sys.exit(1)


def replay_is_premium(slug):
    """Check if replay for this slug passes quality filter. Returns (is_premium, reason)."""
    path = os.path.join(REPLAY_DIR, f'replay_btc-updown-5m-{slug}.json')
    if not os.path.exists(path):
        return False, "no replay file"
    try:
        with open(path) as f: r = json.load(f)
    except Exception as e:
        return False, f"bad JSON: {str(e)[:40]}"

    cols = r.get('tick_columns', [])
    try: cd_i = cols.index('cd')
    except ValueError: return False, "no cd column"

    ticks = r.get('ticks', [])
    valid = [t for t in ticks if t and len(t) > cd_i and t[cd_i] is not None]

    if len(valid) < MIN_TICKS:
        return False, f"sparse ({len(valid)} ticks)"
    first_cd = valid[0][cd_i]
    if first_cd < 300 - MAX_FIRST_CD_SKIP:
        return False, f"late join (first_cd={first_cd:.0f})"
    cds = [t[cd_i] for t in valid]
    intervals = [abs(cds[i] - cds[i+1]) for i in range(len(cds)-1)]
    if intervals and max(intervals) > MAX_TICK_GAP:
        return False, f"gap {max(intervals):.0f}s"

    return True, "ok"


def main():
    print(f"Recap file:   {RECAP_PATH}")
    print(f"Replay dir:   {REPLAY_DIR}")
    print(f"Mode:         {'APPLY' if APPLY else 'DRY RUN'}")
    print()

    if not os.path.exists(RECAP_PATH):
        print(f"ERROR: {RECAP_PATH} not found"); return

    premium = []; non_premium = []
    with open(RECAP_PATH) as f:
        for line in f:
            if not line.strip(): continue
            try: m = json.loads(line)
            except: continue
            slug = m.get('slug', '').replace('btc-updown-5m-','')
            is_premium, reason = replay_is_premium(slug)
            if is_premium:
                premium.append((line, m))
            else:
                non_premium.append((line, m, reason))

    print(f"Total entries:    {len(premium) + len(non_premium)}")
    print(f"Premium (keep):   {len(premium)}")
    print(f"Non-premium:      {len(non_premium)}")

    # Show winner balance for each set
    def balance(entries):
        w = {'UP':0, 'DN':0}
        for _, m, *_ in entries:
            if m.get('winner') in w: w[m['winner']] += 1
        return w

    p_bal = balance(premium)
    n_bal = balance(non_premium)
    print(f"  Premium winners:    UP={p_bal['UP']}, DN={p_bal['DN']}")
    print(f"  Non-premium winners: UP={n_bal['UP']}, DN={n_bal['DN']}")

    # Show reasons
    reason_counts = {}
    for _, _, reason in non_premium:
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
    if reason_counts:
        print(f"\nReasons for non-premium:")
        for reason, count in sorted(reason_counts.items(), key=lambda x: -x[1]):
            print(f"  {count:>3}  {reason}")

    # Show impact on strategy analysis
    print(f"\nImpact on strategy fire counts:")
    def strat_fires(entries):
        sf = {}
        for _, m, *_ in entries:
            for f in m.get('fires', []):
                s = f.get('strategy', 'unknown')
                sf[s] = sf.get(s, 0) + 1
        return sf
    p_sf = strat_fires(premium)
    n_sf = strat_fires(non_premium)
    all_strats = set(p_sf.keys()) | set(n_sf.keys())
    print(f"  {'strategy':<18} {'premium':<10} {'non-prem':<10} {'total':<8}")
    for s in sorted(all_strats, key=lambda k: -(p_sf.get(k,0)+n_sf.get(k,0))):
        p = p_sf.get(s, 0); n = n_sf.get(s, 0)
        print(f"  {s:<18} {p:<10} {n:<10} {p+n:<8}")

    if not APPLY:
        print(f"\n(dry run — add --apply to actually split)")
        return

    if not non_premium:
        print(f"\n✅ Nothing to archive — all entries already premium.")
        return

    # Backup
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    bak_path = f"{RECAP_PATH}.bak.{timestamp}"
    shutil.copy2(RECAP_PATH, bak_path)
    print(f"\n  ✓ backed up to {bak_path}")

    # Write non-premium to archive (append mode)
    archive_path = RECAP_PATH.replace('.jsonl', '.archive.jsonl')
    with open(archive_path, 'a') as f:
        for line, _, _ in non_premium:
            f.write(line if line.endswith('\n') else line + '\n')
    print(f"  ✓ appended {len(non_premium)} entries to {archive_path}")

    # Rewrite recap with only premium
    tmp = RECAP_PATH + '.tmp'
    with open(tmp, 'w') as f:
        for line, _ in premium:
            f.write(line if line.endswith('\n') else line + '\n')
    os.replace(tmp, RECAP_PATH)
    print(f"  ✓ rewrote {RECAP_PATH} with {len(premium)} premium entries")

    print(f"\n✅ Split complete.")
    print(f"  Backup: {bak_path}")
    print(f"  Premium: {RECAP_PATH}")
    print(f"  Archive: {archive_path}")


if __name__ == '__main__':
    main()
