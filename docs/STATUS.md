# Project status

Single source of truth for what works, what doesn't, and what's next. Update in place.
Last audit: 2026-11-21.

## Features

| Feature | Status | Where | Evidence |
| :--- | :--- | :--- | :--- |
| CSV -> MySQL loader | **Verified** | `src/ingest_db.py` | Unit tests (`pytest`); 2026-11-21 real run of the current code against a throwaway MySQL 8.0.43 (5k-row sample of each CSV: 6 tables, blanks stored as NULL, failing file -> exit 1). Full 15.6M-row load last ran on 2025-08-18 with the *previous* version (91.9 min); current version not yet timed on full data. |
| Vendor summary SQL (CTE query) | Verified (2025-08) | notebook, "optimized query" cell | Executed output: 10,692 rows in 0.74 min |
| EDA, metrics, statistics | Verified (2025-08) | notebook | Executed outputs in the notebook |
| Notebook re-runnable from a clean clone | **Unverified** | notebook | Paths/credentials repaired 2026-11-21 (see decisions) but not re-executed end to end: needs a loaded DB |
| Power BI dashboard | **Planned, not started** | none | Notebook exports `data/processed/*.csv` "to use in Power BI"; no `.pbix` exists |

## Decisions

- 2026-11-21: Canonical loader is `src/ingest_db.py`; the notebook's copy of it was removed (it had a
  syntax error and `!pip install logging`, which installs an unrelated Python 2 package). The original
  run output is summarized in the notebook's "Loading the CSVs" cell.
- 2026-11-21: Integer columns are created as BIGINT (was INT) to avoid overflow.
- 2026-11-21: README claims corrected to match the notebook: the speedup came from CTE
  pre-aggregation (no indexes were created); $3.71M is total unsold capital across all vendors;
  the dashboard is planned, not delivered.

## Known issues / tech debt

- Loader reads each CSV fully into memory (`sales.csv` ~1.5 GB on disk, several GB in pandas). Fine
  on the original machine; a chunked reader would need schema inference from a sample.
- VARCHAR sizes are inferred from current data, so a later, longer value would be truncated or fail.
- Dates are stored as VARCHAR (pandas reads them as strings). The notebook's SQL does not depend on
  date types.
- Notebook markdown says Diageo sold "68 million units"; the figure is sales **dollars**.
- Local DB on the owner's machine is named `vender` (set in local `.env`); public default is `vendor`.

## Next steps (ranked)

1. Re-run the notebook top to bottom against the loaded DB to confirm the path/credential fixes.
2. Time a full ingest with the new loader (the old one took 91.9 min).
3. Build the Power BI dashboard from `data/processed/` if still wanted; add a screenshot to the README.
4. Fix the "68 million units" wording; optionally add 2-3 key charts to the README.

## Local-only material (gitignored)

- `archive/`: original drafts kept for history. They contain a plaintext MySQL password, so they
  must never be committed. `draft_v1_*` is an abandoned first notebook (subset of the current one).
- `logs/ingest_db_2025-08-18.log`: log of the original full load.
