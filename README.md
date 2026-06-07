# history-file-maintenance

Maintenance utilities for Polymarket history/recap files: split/archive by slug or replay quality, and filter history down to recap slugs — all with dry-run defaults and timestamped backups.

## Why it exists

The 5-minute crypto up/down trading suite accumulates large append-only JSONL stores (`market_history.jsonl`, `market_recap_history.jsonl`, replay dumps). They grow without bound and mix sparse early-era markets with premium-quality replays. These scripts prune and partition those stores so downstream backtests and strategy analysis run on clean, current, high-quality data — without ever destroying the originals.

## What's inside

| Script | What it does | Splits on |
|---|---|---|
| `split_history_files.py` | Moves old markets out of `market_recap_history.jsonl`, `market_history_lite.jsonl`, and `market_history.jsonl` into `*.archive.jsonl` companions. | Numeric slug threshold (`btc-updown-5m-<n>`, default `< 1776295500`). |
| `split_recap_by_quality.py` | Inspects each recap entry's `replay_btc-updown-5m-<slug>.json` and archives entries whose replay fails the quality bar (≥1500 ticks, `first_cd ≥ 285`, max tick gap ≤ 10s). Reports winner balance and per-strategy fire counts across both sets. | Replay quality, not slug. |
| `filter_history_to_recap.py` | Keeps only history entries whose slug appears in the working recap (optionally also the archived recap); everything else goes to a `*.noncap_archive.jsonl`. | Membership in the recap slug set. |

All three share the same safety model: **dry run is the default**, `--apply` is required to write, originals are copied to `<file>.bak.<timestamp>` before any change, archives are **appended** (never overwritten, so re-runs are safe), and the working file is replaced atomically via a `.tmp` + `os.replace`.

## Requirements

- Python 3 (standard library only — `json`, `os`, `sys`, `glob`, `shutil`, `datetime`; no third-party deps).
- Read/write access to the JSONL/replay files (see **Data**).

## Usage

Run each tool from the directory containing the target JSONL/replay files. Always preview first, then apply.

```bash
# 1. Archive old markets below the slug threshold (preview, then apply)
python3 split_history_files.py
python3 split_history_files.py --apply
python3 split_history_files.py --apply --threshold 1776295500

# 2. Archive recap entries whose replays fail the quality filter
python3 split_recap_by_quality.py
python3 split_recap_by_quality.py --apply
python3 split_recap_by_quality.py --apply --replays /path/to/replays --recap market_recap_history.jsonl

# 3. Filter history down to slugs present in the recap
python3 filter_history_to_recap.py
python3 filter_history_to_recap.py --apply
python3 filter_history_to_recap.py --apply --include-archived-recap   # keep the wider archived recap set
```

## Data

These scripts operate on runtime data stores that live in the private **polymarket-data** repo — `market_history.jsonl`, `market_history_lite.jsonl`, `market_recap_history.jsonl` (and its `.archive.jsonl`), plus per-market `replay_btc-updown-5m-<slug>.json` files. Point each script at that directory (run from inside it, or use `--recap` / `--replays`). No data files are committed here — `*.json`, `*.jsonl`, `*.csv`, `*.gz`, `*.parquet`, and `*.bak.*` are git-ignored.

> Private research software. No warranty; trades/handles real funds at your own risk.
