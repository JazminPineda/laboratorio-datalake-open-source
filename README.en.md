# ELT Batch Ingestion and Data Lake Foundation in Docker

Single-node data lake foundation for batch ingestion, running on Docker Compose.

| Component | Role |
|-----------|------|
| RustFS | S3-compatible object storage, backs all Iceberg table data |
| Nessie | Iceberg REST catalog with git-like versioning |
| Spark | Distributed compute engine, executes PySpark jobs submitted by Airflow |
| Airflow | Pipeline orchestration and scheduling |
| Scrapredis | Dedicated Redis instance used as a job queue between Airflow and external workers |
| Scrapworker | External HTTP ingestion worker. Receives jobs from Scrapredis, fetches data from APIs, and writes raw results to RustFS. Decoupled from Airflow to keep rate limiting and crawl lifecycle outside the orchestration layer |

## Prerequisites
- Cloud vm with 4vCPU, 16GB RAM
- Docker with Compose v2
- `sudo` access (required for RustFS directory ownership)
- Python >=3.14 (for Scrapworker, runs on host)

---

## One-time setup

```bash
# Create the shared Docker network
docker network create data-platform

# Create host directories, set permissions, and download Spark JARs
chmod +x init.sh && ./init.sh
```

---

## Start Order

Start services in this order (shutdown in reverse):

### 1. RustFS

```bash
cd rustfs && docker compose up -d
```

The `rustfs-init` sidecar runs once after RustFS is healthy and creates the `warehouse` bucket automatically.

### 2. Nessie

```bash
cd nessie && docker compose up -d
```

### 3. Spark

```bash
cd spark
docker compose build  # run once before first start
docker compose up -d
```

### 4. Scrapredis

```bash
cd scrapredis && docker compose up -d
```

### 5. Airflow

```bash
cd airflow-docker
docker compose build  # run once before first start
docker compose up -d
```

---

## Bootstrap Namespaces

Run once after Nessie is up. Required before triggering any pipeline:

```bash
curl -X POST http://localhost:19120/iceberg/v1/main/namespaces \
  -H "Content-Type: application/json" \
  -d '{"namespace": ["default"]}'

curl -X POST http://localhost:19120/iceberg/v1/main/namespaces \
  -H "Content-Type: application/json" \
  -d '{"namespace": ["scraper"]}'
```

PowerShell:
```powershell
Invoke-WebRequest -Uri "http://localhost:19120/iceberg/v1/main/namespaces" `
    -Method POST `
    -ContentType "application/json" `
    -Body '{"namespace":["default"]}'

Invoke-WebRequest -Uri "http://localhost:19120/iceberg/v1/main/namespaces" `
    -Method POST `
    -ContentType "application/json" `
    -Body '{"namespace":["scraper"]}'
```


---

## Service URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| RustFS S3 API | http://localhost:9000 | rustfsadmin / rustfsadmin |
| RustFS Console | http://localhost:9001 | rustfsadmin / rustfsadmin |
| Nessie REST catalog | http://localhost:19120/iceberg | |
| Nessie API | http://localhost:19120/api/v2 | |
| Nessie health | http://localhost:9090/q/health | |
| Spark Master UI | http://localhost:8081 | |
| Spark Worker UI | http://localhost:8082 | |
| Airflow UI | http://localhost:8080 | airflow / airflow |

---

## Pipelines

All DAGs are paused at creation. Unpause each one in the Airflow UI before triggering.

| DAG | Description |
|-----|-------------|
| `spark_static_data_v1_skeleton` | Minimal DAG, no Spark. Confirms Airflow scheduler and worker are healthy |
| `spark_static_data_v2_submit` | Writes a static dataset to an Iceberg table via Nessie |
| `spark_partitioned_data_v1` | Extends step2 with time-based partitioning derived from the scheduled slot |
| `scraper_pipeline_v1` | Full ingestion flow via Scrapworker. Requires Scrapworker running (see below) |

---

## Scrapworker

Only required for `scraper_pipeline_v1`. Runs on the host directly (not dockerized):

```bash
uv venv .venv 
cd scrapworker
uv pip install -e .
CONFIG_PATH=./config/config.local.yaml RUSTFS_ACCESS_KEY=rustfsadmin RUSTFS_SECRET_KEY=rustfsadmin python -m scrapworker
```

powershell:
```powershell
uv venv .venv 
cd scrapworker
uv pip install -e .
$env:CONFIG_PATH="./config/config.local.yaml"
$env:RUSTFS_ACCESS_KEY="rustfsadmin"
$env:RUSTFS_SECRET_KEY="rustfsadmin"
python -m scrapworker
```

---

## Stopping

Stop in reverse order:

```bash
cd airflow-docker && docker compose down
cd scrapredis && docker compose down
cd spark && docker compose down
cd nessie && docker compose down
cd rustfs && docker compose down
```

To remove all data (irreversible):

```bash
sudo rm -rf data/
```
>[!WARNING]
> `sudo` is required because RustFS data directories are owned by uid=10001.

powershell:
```powershell
del -Recurse -Force .\data\
```
