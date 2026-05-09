#!/usr/bin/env bash
# -e  exit immediately on error
# -u  treat unset variables as errors
set -eu

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Project root: $SCRIPT_DIR"

# ── RustFS ────────────────────────────────────────────────────────────────────
RUSTFS_DATA="$SCRIPT_DIR/data/rustfs/data"
RUSTFS_LOGS="$SCRIPT_DIR/data/rustfs/applogs"

echo "Creating RustFS data directories..."
echo "  $RUSTFS_DATA"
echo "  $RUSTFS_LOGS"
mkdir -p "$RUSTFS_DATA" "$RUSTFS_LOGS"

echo "Setting ownership for RustFS (uid=10001)..."
sudo chown -R 10001:10001 "$RUSTFS_DATA" "$RUSTFS_LOGS"

# ── Spark ─────────────────────────────────────────────────────────────────────
SPARK_JARS="$SCRIPT_DIR/data/spark/jars"
SPARK_LOGS="$SCRIPT_DIR/data/spark/logs"
SPARK_WORKER="$SCRIPT_DIR/data/spark/worker"

echo "Creating Spark data directories..."
echo "  $SPARK_JARS"
echo "  $SPARK_LOGS"
echo "  $SPARK_WORKER"
mkdir -p "$SPARK_JARS" "$SPARK_LOGS" "$SPARK_WORKER"

echo "Setting ownership for Spark worker (uid=185)..."
sudo chown -R 185:185 "$SPARK_WORKER"

echo "Downloading Spark JARs (skipping if already present)..."
ICEBERG_SPARK_JAR="iceberg-spark-runtime-3.5_2.12-1.10.0.jar"
ICEBERG_AWS_JAR="iceberg-aws-bundle-1.10.1.jar"

[ -f "$SPARK_JARS/$ICEBERG_SPARK_JAR" ] || \
  curl -L -o "$SPARK_JARS/$ICEBERG_SPARK_JAR" \
  "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/1.10.0/$ICEBERG_SPARK_JAR"

[ -f "$SPARK_JARS/$ICEBERG_AWS_JAR" ] || \
  curl -L -o "$SPARK_JARS/$ICEBERG_AWS_JAR" \
  "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-aws-bundle/1.10.1/$ICEBERG_AWS_JAR"

# ── Nessie (Postgres) ─────────────────────────────────────────────────────────
NESSIE_POSTGRES="$SCRIPT_DIR/data/nessie/postgres"

echo "Creating Nessie Postgres data directory..."
echo "  $NESSIE_POSTGRES"
mkdir -p "$NESSIE_POSTGRES"

echo ""
echo "Done. Start services with:"
echo "  cd rustfs && docker compose up -d"
echo "  cd nessie && docker compose up -d"