"""
PySpark script — writes static data with time partition columns to Iceberg.

Invoked by step3_spark_partitioned.py (SparkSubmitOperator).
Receives the scheduled slot time as positional args:
  sys.argv[1]  ds   — date string  e.g. "2026-03-13"
  sys.argv[2]  hr   — hour string  e.g. "14"   (zero-padded, cast to int)
  sys.argv[3]  min  — minute string e.g. "15"  (always 00/15/30/45)

Uses Iceberg DataFrameWriterV2 `.writeTo().overwritePartitions()` instead of
`.write.saveAsTable()`. saveAsTable does not evaluate Iceberg partition specs
during the write, resulting in {NULL, NULL, NULL} partitions. writeTo() uses
the Iceberg-native write path which resolves partition values correctly.
Each run owns exactly one partition (ds/hr/min fixed from scheduled time) —
overwritePartitions() replaces only that partition, leaving all others untouched.
"""

import sys

from pyspark.sql import SparkSession
from pyspark.sql.functions import lit
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

# --- 0. Parse scheduled time args --------------------------------------------
ds  = sys.argv[1]           # "2026-03-13"
hr  = int(sys.argv[2])      # 14
min_ = int(sys.argv[3])     # 15

table = "nessie.default.static_data_partitioned"

print(f"Writing partition: ds={ds}, hr={hr}, min={min_}")

# spark-defaults.conf handles catalog/JAR config
spark = SparkSession.builder.appName("write_partitioned_data").getOrCreate()

# --- 1. Static payload schema ------------------------------------------------
schema = StructType([
    StructField("id",       IntegerType(), nullable=False),
    StructField("name",     StringType(),  nullable=False),
    StructField("category", StringType(),  nullable=True),
    StructField("value",    DoubleType(),  nullable=True),
])

# --- 2. Static data ----------------------------------------------------------
data = [
    (1, "alpha",   "A", 10.5),
    (2, "beta",    "B", 20.0),
    (3, "gamma",   "A", 15.75),
    (4, "delta",   "C", 5.0),
]

# --- 3. Build DataFrame and attach partition columns -------------------------
df = (
    spark.createDataFrame(data, schema=schema)
    .withColumn("ds",  lit(ds))
    .withColumn("hr",  lit(hr).cast(IntegerType()))
    .withColumn("min", lit(min_).cast(IntegerType()))
)

df.printSchema()
df.show()

# --- 4. Ensure partitioned table exists (idempotent) -------------------------
spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {table} (
        id       INT     NOT NULL,
        name     STRING  NOT NULL,
        category STRING,
        value    DOUBLE,
        ds       STRING  NOT NULL,
        hr       INT     NOT NULL,
        min      INT     NOT NULL
    ) USING iceberg
    PARTITIONED BY (ds, hr, min)
    TBLPROPERTIES ('write.format.default' = 'parquet')
""")

# --- 5. Write — overwrites this partition only, preserves all others ---------
# writeTo() uses Iceberg's native write path: evaluates partition values from
# the data and overwrites only matching partitions. saveAsTable() skips
# Iceberg partition evaluation, producing {NULL, NULL, NULL} partitions.
df.writeTo(table).overwritePartitions()

print(f"Done. Partition ds={ds}, hr={hr}, min={min_} written to {table}")

spark.stop()
