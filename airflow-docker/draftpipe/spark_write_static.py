"""
PySpark script — writes static data to an Iceberg table via Nessie catalog.

This script is submitted by SparkSubmitOperator (step2_spark_submit.py).
spark-defaults.conf on the Spark cluster handles all catalog/JAR config.

Schema is defined explicitly so Spark rejects bad data at DataFrame creation,
before anything touches the table.

--- Decision log -----------------------------------------------------------

2026-03-10  Replaced .createOrReplace() with CREATE TABLE IF NOT EXISTS +
            df.write.mode("overwrite").saveAsTable().

            Previous behaviour: .createOrReplace() dropped and recreated the
            table on every 15-min run. Each run produced a new table UUID and
            a new storage prefix in RustFS, leaving the previous run's parquet
            files orphaned. Nessie commit history pointed to those orphaned
            metadata trees, so time-travel queries returned "No Content found".

            New behaviour: the table is created once (idempotent SQL). Every
            subsequent run adds a new Iceberg snapshot on the same table UUID.
            Nessie history is now meaningful — each commit maps to a real,
            queryable snapshot and time-travel works as expected.

            Use .createOrReplace() only when a breaking schema change or a
            full table redefinition is intentional; not for recurring pipelines
            where snapshot history is the point.
----------------------------------------------------------------------------
"""

from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, IntegerType, StringType, DoubleType

# spark-defaults.conf already configures extensions + nessie catalog
spark = SparkSession.builder.appName("write_static_data").getOrCreate()

# --- 1. Define schema explicitly -------------------------------------------
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

# --- 3. Create DataFrame — Spark validates against schema here ---------------
df = spark.createDataFrame(data, schema=schema)
df.printSchema()
df.show()

# --- 4. Ensure table exists (idempotent) ------------------------------------
spark.sql("""
    CREATE TABLE IF NOT EXISTS nessie.default.static_data (
        id       INT     NOT NULL,
        name     STRING  NOT NULL,
        category STRING,
        value    DOUBLE
    ) USING iceberg
    TBLPROPERTIES ('write.format.default' = 'parquet')
""")

# --- 5. Write to Iceberg via Nessie — new snapshot each run -----------------
# mode("overwrite") replaces all rows but keeps the same table UUID, so every
# run produces a new Iceberg snapshot reachable via Nessie history.
(
    df.write
    .format("iceberg")
    .mode("overwrite")
    .saveAsTable("nessie.default.static_data")
)

spark.stop()
