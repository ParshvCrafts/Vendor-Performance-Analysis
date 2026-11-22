# Project status

Single source of truth for what works, what doesn't, and what's next. Update in place.
Last audit: 2026-11-22.

## Features

| Feature | Status | Where | Evidence |
| :--- | :--- | :--- | :--- |
| CSV -> MySQL loader | **Verified** | `src/ingest_db.py` | Unit tests (`pytest`); 2026-11-21 real run against a throwaway MySQL 8.0.43 (5k-row sample per CSV: 6 tables, blanks -> NULL, bad file -> exit 1). Full 15.6M-row load last ran 2025-08-18 with the *previous* version (91.9 min); current version not timed on full data. |
| Notebook (EDA, summary SQL, metrics, statistics) | **Verified 2026-11-22** | `notebooks/` | Executed top to bottom against the local `vender` DB with zero errors (slow-query demo cell skipped). Reproduced: $3.71M unsold capital, t = -17.644, CIs 30.74-31.61 / 40.48-42.62. Committed outputs are still from the Aug 2025 run. |
| Power BI dashboard | **Exists, not re-verified** | `dashboard/Vendor Performance Dashboard.pbix` | Built Aug 2025 by the owner; 1 page: 5 KPI cards, top-10 purchase donut, top vendors/brands bars, low-turnover funnel, low-performing brands scatter. Not opened here (Power BI Desktop not installed). |

## Decisions

- 2026-11-21: Canonical loader is `src/ingest_db.py`; the notebook's broken copy was removed.
- 2026-11-21: Integer columns are BIGINT (was INT) to avoid overflow.
- 2026-11-21: README claims corrected where they contradicted notebook output (speedup came from
  CTE pre-aggregation, not indexes; $3.71M is unsold capital across all vendors).
- 2026-11-22: Ratios that divide by zero (178 zero-sales rows) are stored as NULL, not +/-inf:
  current mysql-connector rejects inf. Analysis filters `ProfitMargin > 0`, so results are unchanged.
- 2026-11-22: Notebook read connections use `autocommit=True`; otherwise reading
  `vendor_sales_summary` after `to_sql(if_exists="replace")` fails with MySQL error 1412.

## Known issues / tech debt

- **Query timing:** the optimized summary query measured 44 s in Aug 2025 but ~181 s on two warm
  re-runs on 2026-11-22. MySQL's `innodb_buffer_pool_size` is the 128 MB default vs a 2.1 GB `sales`
  table, so the query is disk-bound. Raising it (e.g. 4G in `C:\ProgramData\MySQL\MySQL Server 8.0\my.ini`,
  needs admin) would likely help; not tried.
- **Dashboard:** KPI card uses `Sum(ProfitMargin)`, which adds up per-row percentages (should
  probably be Average or SUM(GrossProfit)/SUM(TotalSalesDollars)); the brands bar chart is titled
  "Top Vendors by Sales"; its CSV sources moved from the repo root to `data/processed/`, so Refresh
  needs the source paths updated. All unconfirmed until opened in Power BI Desktop.
- Loader reads each CSV fully into memory; VARCHAR sizes are inferred from current data; dates are
  stored as VARCHAR.
- Notebook markdown says Diageo sold "68 million units"; the figure is sales **dollars**.
- `target` DB (another project) contains an empty `vendor_sales_summary` table created by an old
  version of this notebook. Safe to drop; left in place.

## Runbook

- Start MySQL (service `MySQL80` is Manual start, needs admin): `Start-Service MySQL80` in an admin
  PowerShell. Local DB is `vender` (already loaded; no need to re-ingest).
- Execute the notebook headless (Windows Store Python leaks its global Jupyter into the venv, so the
  venv kernel must be registered and found via `JUPYTER_PATH`):
  `venv\Scripts\python -m ipykernel install --sys-prefix --name vendor-venv`, then from `notebooks/`
  with `JUPYTER_PATH=..\venv\share\jupyter`:
  `..\venv\Scripts\python -m jupyter nbconvert --to notebook --execute --ExecutePreprocessor.kernel_name=vendor-venv --output _verify_run_out.ipynb <copy>.ipynb`.
  Run a copy with the slow-query cell (the one whose saved output is KeyboardInterrupt) blanked.

## Next steps (ranked)

1. Owner: open the dashboard, repoint sources to `data/processed/`, check the two visual issues
   above, export a screenshot to `docs/images/dashboard.png` and add it to the README.
2. Decide how to present the query timing (see Known issues).
3. Time a full ingest with the new loader (old one: 91.9 min). Use a different `MYSQL_DATABASE`
   to avoid dropping `vender`.
4. Fix the "68 million units" wording.

## Local-only material (gitignored)

- `archive/`: original drafts (contain a plaintext MySQL password; never commit).
- `logs/`: `ingest_db_2025-08-18.log` (original full load), `verify_run.txt` (latest notebook run).
