# Infraestructura de Ingesta y Base de Datos (ELT) en Docker

Este proyecto despliega un laboratorio local diseñado para implementar una capa de ingesta de datos robusta, escalable y basada íntegramente en tecnologías de código abierto. El enfoque principal es establecer los cimientos técnicos de un Data Lake —cubriendo el almacenamiento de objetos, el formato de tabla y la catalogación— antes de escalar hacia capas de analítica o gobernanza.

A diferencia de las implementaciones teóricas, este repositorio aborda directamente fallos reales de integración, como discrepancias de versiones en entornos Python y configuraciones críticas de catálogos y particiones.

**Objetivos y Tecnologías Core**
El laboratorio levanta un entorno de nodo único mediante Docker Compose que integra:

* Capa de Almacenamiento: RustFS (Object Storage).

* Formato de Tabla y Catálogo: Apache Iceberg gestionado a través de Project Nessie para control de versiones de datos.

* Orquestación y Procesamiento: Apache Airflow gestionando procesos por lotes (Batch) con PySpark.

* Patrón de Ingesta Real: Desacoplamiento de procesos mediante Redis, utilizando un web scraper externo que interactúa con tablas de señales (signals).

**Alcance del Proyecto:** Este laboratorio se centra estrictamente en la "E" (Extracción) y la base de la carga dentro de un flujo ELT.

**Incluido:** Configuración de infraestructura, gestión de metadatos, particionamiento de tablas Iceberg y orquestación de la ingesta.

**Fuera de alcance:** Transformaciones complejas (dbt), motores de consulta distribuida (Trino) o visualización (Superset). Estas herramientas representan la capa subsiguiente que se apoyará sobre la base construida aquí.


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

powershell:
```powershell
Invoke-WebRequest -Uri http://localhost:19120/iceberg/v1/main/namespaces -Method POST -Headers @{"Content-Type"="application/json"} -Body '{"namespace": ["default"]}'

Invoke-WebRequest -Uri http://localhost:19120/iceberg/v1/main/namespaces -Method POST -Headers @{"Content-Type"="application/json"} -Body '{"namespace": ["scraper"]}'
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
cd scrapworker
pip install -e .
CONFIG_PATH=./config/config.local.yaml RUSTFS_ACCESS_KEY=rustfsadmin RUSTFS_SECRET_KEY=rustfsadmin python -m scrapworker
```

powershell:
```powershell
cd scrapworker
pip install -e .
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
