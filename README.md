# history-file-maintenance

Scripts to split, archive, and filter the Polymarket 5m crypto up/down JSONL history and recap stores. All default to dry-run and back up originals before writing.

## Scripts

`split_history_files.py`: archives entries below a numeric slug threshold out of `market_recap_history.jsonl`, `market_history_lite.jsonl`, and `market_history.jsonl` into `*.archive.jsonl` companions. Threshold defaults to slug `< 1776295500` (`btc-updown-5m-<n>`), override with `--threshold`.

`split_recap_by_quality.py`: archives recap entries whose replay (`replay_btc-updown-5m-<slug>.json`) fails the quality bar. A replay passes if the file exists, has >= 1500 ticks, `first_cd >= 285` (joined within 15s of open), and max tick gap <= 10s. Also reports UP/DN winner balance and per-strategy fire counts for both sets.

`filter_history_to_recap.py`: keeps only history entries whose slug is in the working recap, archiving the rest to `*.noncap_archive.jsonl`. `--include-archived-recap` also matches the `.archive.jsonl` recap (30-slug set vs the current 13).

## Safety model

Dry run is the default; pass `--apply` to write. Originals are copied to `<file>.bak.<timestamp>` first. Archives are appended, never overwritten, so re-runs are safe. The working file is replaced atomically via a `.tmp` and `os.replace`.

## Usage

Run from the directory holding the JSONL/replay files. Preview, then apply.

```bash
python3 split_history_files.py
python3 split_history_files.py --apply
python3 split_history_files.py --apply --threshold 1776295500

python3 split_recap_by_quality.py
python3 split_recap_by_quality.py --apply
python3 split_recap_by_quality.py --apply --replays $DATA_DIR/replays --recap market_recap_history.jsonl

python3 filter_history_to_recap.py
python3 filter_history_to_recap.py --apply
python3 filter_history_to_recap.py --apply --include-archived-recap
```

## Data

Operates on the runtime stores in the private polymarket-data repo: `market_history.jsonl`, `market_history_lite.jsonl`, `market_recap_history.jsonl` (and its `.archive.jsonl`), plus per-market `replay_btc-updown-5m-<slug>.json`. Run from inside that directory or point at it with `--recap` / `--replays`. No data is committed here; `*.json`, `*.jsonl`, `*.csv`, `*.gz`, `*.parquet`, and `*.bak.*` are git-ignored.

Python 3 standard library only; no third-party deps.

Mutates real history files. Always preview with the default dry run before `--apply`.
