"""
Scraper pipeline — triggers scrapworker via Redis and publishes signal to Nessie.

Flow:
  submit_job → wait_for_completion → publish_nessie_signal

- submit_job        : pushes job payload to Redis (scrapworker:jobs)
- wait_for_completion: polls Redis status key until finished/failed
- publish_nessie_signal: reads s3_path from status key, writes Iceberg signal row

Partition values (ds, hr, min) are derived from data_interval_start so reruns
for the same scheduled slot always produce the same path and partition values.

To promote: copy this file into dags/.
"""

import json
import logging
import time
from datetime import datetime

import redis
from airflow.decorators import dag, task
from airflow.exceptions import AirflowFailException
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

log = logging.getLogger(__name__)

POLL_INTERVAL = 10  # seconds

ENDPOINT = "BINANCE_TRADES"
QUERY = {"symbol": "BTCUSDT", "limit": 10}
REDIS_HOST = "scrapredis"
REDIS_PORT = 6379
QUEUE_KEY = "scrapworker:jobs"


@dag(
    dag_id="scraper_pipeline_v1",
    schedule="*/15 * * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["draft", "scraper"],
)
def pipeline():

    @task
    def submit_job(data_interval_start=None, run_id=None):
        # by default the code gets wrapper in PythonOperator
        ds = data_interval_start.strftime("%Y-%m-%d")
        hr = data_interval_start.strftime("%H")
        minute = data_interval_start.strftime("%M")

        s3_path = f"raw/scraper/{ENDPOINT}/{ds}/{hr}/{minute}/data.json"

        payload = {
            "run_id": run_id,
            "endpoint": ENDPOINT,
            "params": QUERY,
            "s3_path": s3_path,
        }

        client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        client.lpush(QUEUE_KEY, json.dumps(payload))

    @task
    def wait_for_completion(run_id=None):
        status_key = f"scrapworker:status:{run_id}"
        client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

        attempt = 0
        while True:
            attempt += 1
            raw = client.get(status_key)

            if raw is None:
                log.info("Attempt %d | key absent (pending TTL expired or not yet set)", attempt)
            else:
                status_data = json.loads(raw)
                status = status_data.get("status")
                log.info("Attempt %d | status_key=%s | response=%s", attempt, status_key, status_data)

                if status == "finished":
                    return
                if status == "failed":
                    raise AirflowFailException(f"Job {run_id} failed: {status_data}")

            time.sleep(POLL_INTERVAL)

    publish_signal = SparkSubmitOperator(
        task_id="publish_nessie_signal",
        conn_id="spark_default",
        application="/opt/airflow/dags/scraper_signal_publish.py",
        deploy_mode="client",
        verbose=True,
        application_args=[
            "{{ run_id }}",
            ENDPOINT,
            "{{ data_interval_start | ds }}",
            "{{ data_interval_start.strftime('%H') }}",
            "{{ data_interval_start.strftime('%M') }}",
        ],
    )

    submit = submit_job()
    wait = wait_for_completion()
    submit >> wait >> publish_signal


pipeline()
