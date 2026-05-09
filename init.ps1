# ErrorActionPreference "Stop" equivale a set -e (salir inmediatamente en error)
# Set-StrictMode -Version Latest ayuda a detectar variables no definidas (similar a set -u)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$SCRIPT_DIR = $PSScriptRoot
Write-Host "Project root: $SCRIPT_DIR"

# ── RustFS ────────────────────────────────────────────────────────────────────
$RUSTFS_DATA = Join-Path $SCRIPT_DIR "data\rustfs\data"
$RUSTFS_LOGS = Join-Path $SCRIPT_DIR "data\rustfs\applogs"

Write-Host "Creating RustFS data directories..."
Write-Host "  $RUSTFS_DATA"
Write-Host "  $RUSTFS_LOGS"
New-Item -ItemType Directory -Force -Path $RUSTFS_DATA | Out-Null
New-Item -ItemType Directory -Force -Path $RUSTFS_LOGS | Out-Null

Write-Host "Setting ownership for RustFS (uid=10001)..."
Write-Host "  (Skipped on Windows - ownership/permissions work differently)"
# Nota: En Windows no hay UIDs como en Linux. Si estás usando Docker con Linux containers,
# la gestión de permisos se maneja diferente. Descomentar si es necesario:
# icacls $RUSTFS_DATA /grant "Everyone:(OI)(CI)F" /T
# icacls $RUSTFS_LOGS /grant "Everyone:(OI)(CI)F" /T

# ── Spark ─────────────────────────────────────────────────────────────────────
$SPARK_JARS = Join-Path $SCRIPT_DIR "data\spark\jars"
$SPARK_LOGS = Join-Path $SCRIPT_DIR "data\spark\logs"
$SPARK_WORKER = Join-Path $SCRIPT_DIR "data\spark\worker"

Write-Host "Creating Spark data directories..."
Write-Host "  $SPARK_JARS"
Write-Host "  $SPARK_LOGS"
Write-Host "  $SPARK_WORKER"
New-Item -ItemType Directory -Force -Path $SPARK_JARS | Out-Null
New-Item -ItemType Directory -Force -Path $SPARK_LOGS | Out-Null
New-Item -ItemType Directory -Force -Path $SPARK_WORKER | Out-Null

Write-Host "Setting ownership for Spark worker (uid=185)..."
Write-Host "  (Skipped on Windows - ownership/permissions work differently)"
# icacls $SPARK_WORKER /grant "Everyone:(OI)(CI)F" /T

Write-Host "Downloading Spark JARs (skipping if already present)..."
$ICEBERG_SPARK_JAR = "iceberg-spark-runtime-3.5_2.12-1.10.0.jar"
$ICEBERG_AWS_JAR = "iceberg-aws-bundle-1.10.1.jar"

$ICEBERG_SPARK_JAR_PATH = Join-Path $SPARK_JARS $ICEBERG_SPARK_JAR
if (-not (Test-Path $ICEBERG_SPARK_JAR_PATH)) {
    Write-Host "  Downloading $ICEBERG_SPARK_JAR..."
    Invoke-WebRequest -Uri "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/1.10.0/$ICEBERG_SPARK_JAR" `
        -OutFile $ICEBERG_SPARK_JAR_PATH
} else {
    Write-Host "  $ICEBERG_SPARK_JAR already exists, skipping..."
}

$ICEBERG_AWS_JAR_PATH = Join-Path $SPARK_JARS $ICEBERG_AWS_JAR
if (-not (Test-Path $ICEBERG_AWS_JAR_PATH)) {
    Write-Host "  Downloading $ICEBERG_AWS_JAR..."
    Invoke-WebRequest -Uri "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-aws-bundle/1.10.1/$ICEBERG_AWS_JAR" `
        -OutFile $ICEBERG_AWS_JAR_PATH
} else {
    Write-Host "  $ICEBERG_AWS_JAR already exists, skipping..."
}

# ── Nessie (Postgres) ─────────────────────────────────────────────────────────
$NESSIE_POSTGRES = Join-Path $SCRIPT_DIR "data\nessie\postgres"

Write-Host "Creating Nessie Postgres data directory..."
Write-Host "  $NESSIE_POSTGRES"
New-Item -ItemType Directory -Force -Path $NESSIE_POSTGRES | Out-Null

Write-Host ""
Write-Host "Done. Start services with:"
Write-Host "  cd rustfs && docker compose up -d"
Write-Host "  cd nessie && docker compose up -d"