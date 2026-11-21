"""Load every CSV in DATA_DIR into its own MySQL table.

WARNING: each run DROPS and recreates MYSQL_DATABASE so repeated runs never
duplicate rows. Point MYSQL_DATABASE at a database you are happy to lose.

Configuration comes from the environment (or a .env file at the repo root);
see .env.example. Exit code is non-zero if any table fails to load.
"""
import logging
import os
import sys
import time
from pathlib import Path

import mysql.connector
import pandas as pd
from dotenv import load_dotenv
from mysql.connector import Error

REPO_ROOT = Path(__file__).resolve().parent.parent
BATCH_SIZE = 1000  # rows per INSERT; keeps packets well under max_allowed_packet
MAX_RETRIES = 3

log = logging.getLogger("ingest_db")


def load_config():
    """Read settings from the environment; fail fast on a missing password."""
    load_dotenv(REPO_ROOT / ".env")
    password = os.getenv("MYSQL_PASSWORD")
    if not password:
        raise SystemExit("MYSQL_PASSWORD is not set. Copy .env.example to .env and fill it in.")
    return {
        "db": {
            "host": os.getenv("MYSQL_HOST", "localhost"),
            "port": int(os.getenv("MYSQL_PORT", "3306")),
            "user": os.getenv("MYSQL_USER", "root"),
            "password": password,
            "database": os.getenv("MYSQL_DATABASE", "vendor"),
        },
        "data_dir": Path(os.getenv("DATA_DIR", REPO_ROOT / "data" / "raw")),
        "log_dir": Path(os.getenv("LOG_DIR", REPO_ROOT / "logs")),
    }


def setup_logging(log_dir):
    log_dir.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler = logging.FileHandler(log_dir / "ingest_db.log", mode="a")
    console = logging.StreamHandler()
    for handler in (file_handler, console):
        handler.setFormatter(fmt)
        log.addHandler(handler)
    log.setLevel(logging.INFO)


def discover_csv_files(data_dir):
    """Return [(file_name, table_name)] for each *.csv directly in data_dir, sorted."""
    return [(p.name, p.stem) for p in sorted(Path(data_dir).glob("*.csv"))]


def get_sql_type(series):
    """Map a pandas column to a MySQL column type."""
    dtype = series.dtype
    if pd.api.types.is_bool_dtype(dtype):
        return "BOOLEAN"
    if pd.api.types.is_integer_dtype(dtype):
        # BIGINT: INT overflows above 2,147,483,647 and pandas ints are 64-bit.
        return "BIGINT"
    if pd.api.types.is_float_dtype(dtype):
        return "DOUBLE"
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "DATETIME"
    max_length = series.dropna().astype(str).str.len().max()
    if pd.isna(max_length) or max_length == 0:
        return "VARCHAR(255)"
    if max_length <= 255:
        # 20% headroom, at least 50, never above 255.
        return f"VARCHAR({min(255, max(50, int(max_length * 1.2)))})"
    return "TEXT"


def to_db_rows(df):
    """Convert a DataFrame slice to tuples of plain Python values, NaN -> None.

    astype(object) turns numpy scalars into Python int/float, which the MySQL
    connector can bind; numpy types are rejected by some connector versions.
    """
    return list(df.astype(object).where(df.notna(), None).itertuples(index=False, name=None))


def clean_column_name(col):
    return col.replace(" ", "_").replace("-", "_").replace(".", "_")


def connect(db_config, with_database=True):
    """Connect with retries; try ssl_disabled first, then default SSL."""
    config = dict(db_config)
    if not with_database:
        del config["database"]
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        for extra in ({"ssl_disabled": True}, {}):
            try:
                conn = mysql.connector.connect(**config, **extra)
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                cursor.close()
                return conn
            except (Error, AttributeError) as e:
                last_error = e
                log.warning("Connection attempt %d (%s) failed: %s", attempt, extra or "default SSL", e)
        if attempt < MAX_RETRIES:
            time.sleep(5 * attempt)
    raise ConnectionError(f"Could not connect to MySQL after {MAX_RETRIES} attempts: {last_error}")


def recreate_database(db_config):
    name = db_config["database"]
    conn = connect(db_config, with_database=False)
    try:
        cursor = conn.cursor()
        cursor.execute(f"DROP DATABASE IF EXISTS `{name}`")
        cursor.execute(f"CREATE DATABASE `{name}`")
        cursor.close()
        log.info("Database '%s' dropped and recreated", name)
    finally:
        conn.close()


def upload_csv_to_table(db_config, file_path, table_name):
    """Create table_name from the CSV's columns and insert all rows in batches."""
    log.info("Processing %s...", file_path.name)
    df = pd.read_csv(file_path)
    if df.empty:
        log.warning("%s is empty; skipped", file_path.name)
        return 0
    df.columns = [clean_column_name(c) for c in df.columns]
    log.info("Loaded %s rows from %s", f"{len(df):,}", file_path.name)

    columns_sql = ", ".join(f"`{col}` {get_sql_type(df[col])}" for col in df.columns)
    columns_str = ", ".join(f"`{col}`" for col in df.columns)
    placeholders = ", ".join(["%s"] * len(df.columns))
    insert_query = f"INSERT INTO `{table_name}` ({columns_str}) VALUES ({placeholders})"

    conn = connect(db_config)
    try:
        cursor = conn.cursor()
        cursor.execute(f"CREATE TABLE `{table_name}` ({columns_sql})")
        rows_inserted = 0
        for start in range(0, len(df), BATCH_SIZE):
            batch = to_db_rows(df.iloc[start:start + BATCH_SIZE])
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    cursor.executemany(insert_query, batch)
                    conn.commit()
                    break
                except Error as e:
                    log.warning("Batch at row %d, attempt %d failed: %s", start, attempt, e)
                    if attempt == MAX_RETRIES:
                        raise
                    conn.close()
                    time.sleep(2 * attempt)
                    conn = connect(db_config)
                    cursor = conn.cursor()
            rows_inserted += len(batch)
        log.info("Inserted %s rows into '%s'", f"{rows_inserted:,}", table_name)
        return rows_inserted
    finally:
        conn.close()


def main():
    config = load_config()
    setup_logging(config["log_dir"])
    db_config, data_dir = config["db"], config["data_dir"]

    csv_files = discover_csv_files(data_dir)
    if not csv_files:
        raise SystemExit(f"No CSV files found in {data_dir}")
    log.info("Found %d CSV files in %s: %s", len(csv_files), data_dir, [f for f, _ in csv_files])

    start = time.time()
    recreate_database(db_config)

    failed = []
    for file_name, table_name in csv_files:
        try:
            upload_csv_to_table(db_config, data_dir / file_name, table_name)
        except Exception as e:
            log.error("Failed to load %s: %s", file_name, e)
            failed.append(file_name)

    conn = connect(db_config)
    try:
        cursor = conn.cursor()
        for file_name, table_name in csv_files:
            if file_name in failed:
                continue
            cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
            log.info("Table '%s': %s rows", table_name, f"{cursor.fetchone()[0]:,}")
    finally:
        conn.close()

    log.info("Ingestion finished in %.2f minutes", (time.time() - start) / 60)
    if failed:
        log.error("%d table(s) failed: %s", len(failed), failed)
        sys.exit(1)


if __name__ == "__main__":
    main()
