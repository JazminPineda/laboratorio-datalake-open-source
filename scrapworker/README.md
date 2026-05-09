## scrapworker

Redis-driven scrape worker. Blocks on a Redis queue, pops a job payload, executes the HTTP request via Scrapy, and writes results to RustFS.

### Build System

Uses [Hatchling](https://hatch.pypa.io/latest/) (PEP 517/518). Project metadata and dependencies are declared in `pyproject.toml`. No `requirements.txt`. dependencies are managed through the package itself.

### Commands

```bash
# Install the package in editable mode (for local dev / IDE support)
pip install -e .
```
Installs scrapworker into the current Python environment as an editable package. Makes the `scrapworker` entry point available and enables IDE autocomplete. Not needed when running via Docker.

```bash
# Run the worker
python -m scrapworker
```
Starts the worker process via `scrapworker/__main__.py`. Connects to Redis and blocks indefinitely waiting for jobs. Each job triggers a Scrapy crawl subprocess.

### Configuration

Mount the `config/` directory as a volume. The worker reads `config/config.yaml` for Redis endpoint, RustFS endpoint, and endpoint URL registry.

Credentials (RustFS access key/secret) are passed as environment variables.

### Future Improvements

- **Config validation at startup**: validate required fields (e.g. `offset_param`, `page_size_param` for paginated schemas) when config loads, rather than failing silently at runtime with wrong defaults. A `validate_config()` call in `load_config()` would catch misconfigured schemas early.
- **Deep merge for schema overrides**: the current `resolve_endpoint()` does a shallow merge of schema + endpoint config. This means overriding a single nested key (e.g. one field inside `response_map`) replaces the entire nested dict rather than merging it. A recursive deep merge would allow endpoints to partially override schema blocks without repeating all sibling keys.

### Docker

```bash
# docker build -t scrapworker .
# docker compose up -d

# local run
CONFIG_PATH=./config/config.local.yaml python -m scrapworker

CONFIG_PATH=./config/config.local.yaml RUSTFS_ACCESS_KEY=rustfsadmin RUSTFS_SECRET_KEY=rustfsadmin python -m scrapworker
```

## Redis Connection and manual example payload
```bash
redis-cli -p 6380
# or
docker exec -it scrapredis redis-cli

LPUSH scrapworker:jobs '{"endpoint": "BINANCE_TRADES", "run_id": "bin001", "params": {"symbol": "BTCUSDT", "limit": 10}, "s3_path": "raw/scraper/BINANCE_TRADES/2026/04/11/10/data.json"}'
```
