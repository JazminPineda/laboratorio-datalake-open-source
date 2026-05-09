import json
import logging
import multiprocessing
import socket
import sys

import redis

from scrapworker.config import load_config
from scrapworker.crawler import run

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def main():
    config = load_config()
    redis_cfg = config["redis"]

    worker_id = socket.gethostname()
    log.info("Worker ID: %s", worker_id)

    log.info("Connecting to Redis at %s:%s", redis_cfg["host"], redis_cfg["port"])
    try:
        client = redis.Redis(
            host=redis_cfg["host"],
            port=redis_cfg["port"],
            decode_responses=True,
        )
        client.ping()
    except redis.exceptions.ConnectionError as e:
        log.error("Failed to connect to Redis: %s", e)
        sys.exit(1)

    log.info("Connected. Waiting for jobs on '%s'", redis_cfg["queue_key"])

    PENDING_TTL = 60                  # 1 minute — short, for exactly-once guarantee
    TERMINAL_TTL = 7 * 24 * 60 * 60  # 7 days — for running/finished/failed

    while True:
        _, payload = client.blpop(redis_cfg["queue_key"])
        job = json.loads(payload)
        run_id = job["run_id"]
        log.info("Received job: %s", job)

        status_key = f"scrapworker:status:{run_id}"

        existing = client.get(status_key)
        if existing:
            existing_status = json.loads(existing).get("status")
            log.info("Skipping job run_id=%s, status already: %s", run_id, existing_status)
            continue

        client.set(status_key, json.dumps({"status": "pending", "worker_id": worker_id}), ex=PENDING_TTL)
        log.info("Status set to pending for run_id=%s", run_id)

        client.set(status_key, json.dumps({"status": "running", "worker_id": worker_id}), ex=TERMINAL_TTL)
        log.info("Status set to running for run_id=%s", run_id)

        process = multiprocessing.Process(target=run, args=(job, config, worker_id))
        process.start()
        process.join()

        if process.exitcode == 0:
            client.set(status_key, json.dumps({"status": "finished", "worker_id": worker_id, "s3_path": job["s3_path"]}), ex=TERMINAL_TTL)
            log.info("Status set to finished for run_id=%s | s3_path=%s", run_id, job["s3_path"])
        else:
            client.set(status_key, json.dumps({"status": "failed", "worker_id": worker_id}), ex=TERMINAL_TTL)
            log.error("Status set to failed for run_id=%s (exit code %s)", run_id, process.exitcode)
