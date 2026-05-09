# Compose Orchestration

> **Status: Unstable** not fully tested end-to-end. Use per-folder `docker compose up/down` for reliable startup.

Unified startup and shutdown for the full data platform stack from a single root directory,
replacing the previous per-folder `docker compose up/down` workflow.

## Files

| File | Purpose |
|------|---------|
| `docker-compose.yaml` | Declares the project. Uses `include` to pull in all sub-stack compose files. No services defined here directly. |
| `docker-compose.override.yaml` | **Orchestration layer.** Auto-merged by Compose. Adds profiles, healthchecks, and cross-stack `depends_on`. Individual compose files are not modified. |

Docker Compose automatically merges these two files — no `-f` flag needed. Run all commands from the
`data-platform/` root.

---

## Profiles

| Profile | Stacks started |
|---------|----------------|
| `spark` | rustfs → nessie → spark → airflow |
| `all` | rustfs → nessie → spark → airflow + trino |

Services without a matching profile are not started. Startup order is enforced by `depends_on`
health gates in the override — each stack waits for the previous one to be healthy before starting.

---

## Commands

### Start

```bash
# Spark path only (rustfs + nessie + spark + airflow)
docker compose --profile spark up -d --wait

# Everything including Trino
docker compose --profile all up -d --wait
```

`--wait` blocks until all started services report healthy (or exit 0 for init containers).
Without it, the command returns as soon as containers are created, before they are ready.

### Stop

```bash
# Full teardown — removes containers, respects reverse depends_on order automatically
docker compose down

# Stop without removing containers (preserves state for faster restart)
docker compose --profile spark stop
docker compose --profile all stop
```

### Other

```bash
# Validate merged config (catches YAML errors and broken includes)
docker compose config --quiet && echo "OK"

# Inspect the fully merged config (useful for debugging override merges)
docker compose config

# Service status
docker compose ps

# Tail logs for a specific service
docker compose logs -f nessie
```

---

## How the override works

### Profiles

Profiles are declared in the override, not in individual compose files. This keeps each sub-stack's
compose file self-contained and runnable independently (e.g. `cd nessie && docker compose up`).

```yaml
# docker-compose.override.yaml
services:
  rustfs:
    profiles: [spark, all]   # starts with both profiles
  spark-master:
    profiles: [spark, all]   # spark path only
  trino-coordinator:
    profiles: [all]          # all profile only
```

### Healthchecks

The override declares healthchecks for services that need them for cross-stack gating.
The rustfs healthcheck is the exception — it was already defined in `rustfs/docker-compose.yaml`
and is left there unchanged. The override simply references it via `condition: service_healthy`,
demonstrating that a healthcheck can be defined in one file and consumed from another.

```
rustfs        ← healthcheck defined in rustfs/docker-compose.yaml  (unchanged)
nessie        ← healthcheck defined in docker-compose.override.yaml
spark-master  ← healthcheck defined in docker-compose.override.yaml
```

### depends_on chain

```
rustfs (healthy)
  └── nessie (healthy)           depends_on: rustfs
        └── spark-master (healthy)  depends_on: nessie
              └── airflow-init (completed)  depends_on: spark-master
                    └── all airflow services  depend on airflow-init
        └── trino-coordinator    depends_on: nessie  (profile: all)
```

Each arrow means: *do not start until the upstream service is healthy*.

### Trino

Trino is included in `docker-compose.yaml` but only starts with `--profile all`.
Its `depends_on: nessie` gate is declared in the override.

---

## Adding a new stack

1. Add its compose file to the `include` list in `docker-compose.yaml`
2. In `docker-compose.override.yaml`:
   - Add a `profiles` entry for each service
   - Add a `healthcheck` if the service needs to gate downstream stacks
   - Add `depends_on` pointing at whichever upstream service must be healthy first
3. Gate any downstream service on the new stack's healthcheck as needed

---

> **Warning — Airflow startup not fully validated**
>
> The Airflow stack has not been cleanly tested through this orchestration setup yet.
> The `airflow-init` gate on `spark-master: service_healthy` is correct in theory,
> but the full airflow startup sequence (init → scheduler → worker → apiserver) may
> require additional debugging — particularly around timing, profile interactions, and
> the `depends_on` merge behaviour with the existing YAML anchors in
> `airflow-docker/docker-compose.yaml`. Treat the Airflow section of the override as
> a starting point, not a proven configuration.
