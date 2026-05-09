"""
STEP 1 — Bare-minimum DAG skeleton.

Concepts covered:
  - dag_id           : unique name Airflow uses to identify the pipeline
  - schedule         : cron expression (every 15 min here)
  - start_date       : when scheduling begins; use a fixed past date, never `datetime.now()`
  - catchup=False    : don't back-fill all past runs since start_date
  - @task decorator  : turns a plain Python function into an Airflow task (TaskFlow API)
  - Task dependency  : `task_a >> task_b` means b runs after a succeeds

No Spark yet — just verifies Airflow can parse and schedule the file.
"""

from datetime import datetime

from airflow.decorators import dag, task


@dag(
    dag_id="spark_static_data_v1_skeleton",
    schedule="*/15 * * * *",   # every 15 minutes
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["draft", "spark"],
)
def pipeline():

    @task
    def say_hello():
        print("DAG is alive. Next step: submit a Spark job.")

    say_hello()


pipeline()
