# Vendor Performance Analysis

End-to-end ETL and analytics pipeline over **15.6M+ retail transaction records**, built to answer a
question the business could not previously ask cheaply: *which vendors are quietly absorbing working
capital?*

The pipeline ingests raw CSV extracts into MySQL, models them into an analysis-ready vendor sales
summary, and surfaces margin, turnover, and idle-inventory findings through an executive dashboard.

---

## Results

| | |
| :--- | :--- |
| **Records processed** | 15.6M+ transactional rows across 6 source tables |
| **Query performance** | Summary query reduced from **9 min to 44 sec** (~12x) via indexing and query restructuring |
| **Business finding** | **$3.7M** of inventory capital identified as tied up in underperforming vendors |
| **Deliverable** | Vendor-level margin and turnover dashboard for executive review |

The speedup mattered more than the raw number suggests. At nine minutes per query analysts ran one
question a day; at forty-four seconds they explored freely. Making the pipeline interactive changed
what the data was used for.

---

## Stack

`Python` · `Pandas` · `NumPy` · `MySQL` · `SQLAlchemy` · `Matplotlib` · `Seaborn` · `Power BI`

---

## Repository layout

```
ingest_db.py                        Batched CSV -> MySQL loader with logging and error handling
vendor_performance_analysis.ipynb   EDA, feature engineering, vendor scoring, and findings
sample_top_10_vendors.csv           Small sample of the output, for orientation
.env.example                        Template for local configuration
```

---

## Data

The source CSVs are **not committed** — `sales.csv` alone is 1.5 GB, well beyond GitHub's 100 MB
per-file limit. The pipeline expects these files in a local `data/` directory (or wherever `DATA_DIR`
points):

| File | Approx. size |
| :--- | :--- |
| `sales.csv` | 1.5 GB |
| `purchases.csv` | 345 MB |
| `end_inventory.csv` | 19 MB |
| `begin_inventory.csv` | 17 MB |
| `vendor_invoice.csv` | 510 KB |
| `purchase_prices.csv` | 1 MB |

`sample_top_10_vendors.csv` is included so the output shape is clear without the full dataset.

---

## Running it

```bash
git clone https://github.com/ParshvCrafts/Vendor-Performance-Analysis.git
cd Vendor-Performance-Analysis

python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env        # then fill in your MySQL credentials
mkdir -p data               # place the source CSVs here

python ingest_db.py         # loads CSVs into MySQL in batches
jupyter notebook vendor_performance_analysis.ipynb
```

Configuration is read from the environment — no credentials or machine-specific paths are stored in
source control.

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `MYSQL_HOST` | `localhost` | Database host |
| `MYSQL_USER` | `root` | Database user |
| `MYSQL_PASSWORD` | *(required)* | Database password |
| `MYSQL_DATABASE` | `vendor` | Target database |
| `DATA_DIR` | `./data` | Directory holding the source CSVs |
| `LOG_DIR` | `./logs` | Ingestion log output |

---

## Method

1. **Ingest** — stream each CSV into MySQL in 1,000-row batches with per-file logging, so a failure
   part-way through is diagnosable and resumable rather than silent.
2. **Model** — join sales, purchases, invoices, and inventory into a single vendor-level summary with
   derived margin, turnover, and unsold-capital measures.
3. **Optimise** — index the join and filter columns and restructure the summary query; this is where
   the 9 min to 44 sec reduction comes from.
4. **Analyse** — rank vendors on contribution and capital efficiency, isolate the long tail holding
   inventory that is not moving, and quantify the capital involved.

---

## License

MIT
