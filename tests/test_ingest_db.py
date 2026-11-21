import numpy as np
import pandas as pd
import pytest

import ingest_db


def test_discover_only_top_level_csv_sorted(tmp_path):
    # Catches: loose ".csv" in name matching, and nested output folders being ingested.
    (tmp_path / "sales.csv").write_text("a\n1\n")
    (tmp_path / "begin_inventory.csv").write_text("a\n1\n")
    (tmp_path / "notes.csv.bak").write_text("x")
    (tmp_path / "processed").mkdir()
    (tmp_path / "processed" / "summary.csv").write_text("a\n1\n")
    assert ingest_db.discover_csv_files(tmp_path) == [
        ("begin_inventory.csv", "begin_inventory"),
        ("sales.csv", "sales"),
    ]


@pytest.mark.parametrize(
    "series, expected",
    [
        (pd.Series([1, 2]), "BIGINT"),
        (pd.Series([3_000_000_000]), "BIGINT"),  # would overflow MySQL INT
        (pd.Series([1.5, np.nan]), "DOUBLE"),
        (pd.Series([True, False]), "BOOLEAN"),
        (pd.Series(pd.to_datetime(["2024-01-01"])), "DATETIME"),
        (pd.Series(["ab"]), "VARCHAR(50)"),  # floor of 50
        (pd.Series(["x" * 100]), "VARCHAR(120)"),  # 20% headroom
        (pd.Series(["x" * 250]), "VARCHAR(255)"),  # capped at 255
        (pd.Series(["x" * 256]), "TEXT"),
        (pd.Series([None, None], dtype=object), "VARCHAR(255)"),
    ],
)
def test_get_sql_type(series, expected):
    assert ingest_db.get_sql_type(series) == expected


def test_to_db_rows_converts_nan_and_numpy_types():
    # Catches: NaN reaching MySQL as 'nan' and numpy scalars the connector cannot bind.
    df = pd.DataFrame({"n": [1, 2], "f": [1.5, np.nan], "s": ["a", None]})
    rows = ingest_db.to_db_rows(df)
    assert rows == [(1, 1.5, "a"), (2, None, None)]
    assert all(type(v) in (int, float, str, type(None)) for row in rows for v in row)


def test_clean_column_name():
    assert ingest_db.clean_column_name("Purchase Price-v.2") == "Purchase_Price_v_2"


def test_missing_password_fails_fast(monkeypatch):
    monkeypatch.setattr(ingest_db, "load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv("MYSQL_PASSWORD", raising=False)
    with pytest.raises(SystemExit, match="MYSQL_PASSWORD"):
        ingest_db.load_config()
