"""
PySpark script — writes a signal row to scraper.signal Iceberg table in Nessie.

Invoked by scraper_pipeline.py (SparkSubmitOperator).
Receives job details as positional args:
  sys.argv[1]  run_id    — Airflow run_id
  sys.argv[2]  endpoint  — e.g. BINANCE_TRADES
  sys.argv[3]  ds        — date string e.g. "2026-03-28"
  sys.argv[4]  hr        — hour string e.g. "22"
  sys.argv[5]  min       — minute string e.g. "00" / "15" / "30" / "45"

s3_path is constructed from the above args using the standard raw path convention.

Partition overwrite on (ds, hr, min, endpoint) — reruns for the same slot
overwrite the existing signal row, all other partitions untouched.
"""

import sys
from datetime import datetime, timezone

from pyspark.sql import SparkSession
from pyspark.sql.types import StringType, StructField, StructType, TimestampType

run_id   = sys.argv[1]
endpoint = sys.argv[2]
ds       = sys.argv[3]
hr       = sys.argv[4]
min_     = sys.argv[5]

s3_path = f"raw/scraper/{endpoint}/{ds}/{hr}/{min_}/data.json"
table   = "nessie.scraper.signal"

print(f"Publishing signal: run_id={run_id} endpoint={endpoint} ds={ds} hr={hr} min={min_}")

spark = SparkSession.builder.appName("scraper_signal_publish").getOrCreate()

schema = StructType([
    StructField("run_id",       StringType(),    nullable=False),
    StructField("endpoint",     StringType(),    nullable=False),
    StructField("s3_path",      StringType(),    nullable=False),
    StructField("ds",           StringType(),    nullable=False),
    StructField("hr",           StringType(),    nullable=False),
    StructField("min",          StringType(),    nullable=False),
    StructField("published_at", TimestampType(), nullable=False),
])

published_at = datetime.now(timezone.utc).replace(tzinfo=None)

data = [(run_id, endpoint, s3_path, ds, hr, min_, published_at)]

df = spark.createDataFrame(data, schema=schema)

df.printSchema()
df.show(truncate=False)

spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {table} (
        run_id       STRING    NOT NULL,
        endpoint     STRING    NOT NULL,
        s3_path      STRING    NOT NULL,
        ds           STRING    NOT NULL,
        hr           STRING    NOT NULL,
        min          STRING    NOT NULL,
        published_at TIMESTAMP NOT NULL
    ) USING iceberg
    PARTITIONED BY (ds, hr, min, endpoint)
    TBLPROPERTIES ('write.format.default' = 'parquet')
""")

df.writeTo(table).overwritePartitions()

print(f"Done. Signal published for run_id={run_id} ds={ds} hr={hr} min={min_} endpoint={endpoint}")

spark.stop()
