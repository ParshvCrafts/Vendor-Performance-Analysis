# Vendor Performance Analysis

Tier 2 portfolio project (public repo, not deployed). Python + MySQL + Jupyter.

- Status, decisions, known issues, next steps: `docs/STATUS.md` (update it when work lands).
- Loader: `src/ingest_db.py`; tests: `pytest` from repo root (no DB needed).
- Never commit `archive/` or `.env` (plaintext password). Data in `data/raw/` is ~1.9 GB: don't read
  whole files; use `head`.
- `src/ingest_db.py` DROPS the target database. For tests use a throwaway server or DB name.
