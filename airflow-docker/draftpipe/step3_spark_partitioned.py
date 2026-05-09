"""
STEP 3 — Submit a PySpark job that writes time-partitioned data.

New concepts vs step2:
  - application_args   : positional args forwarded to the PySpark script as
                         sys.argv[1], sys.argv[2], sys.argv[3].
  - Jinja templating   : {{ data_interval_start }} is the *scheduled* run time
                         (not wall-clock time), so reruns for the same slot
                         always produce the same partition values.
  - data_interval_start: for a 15-min schedule this is the left edge of the
                         interval — gives minutes 0, 15, 30, 45.

To promote: copy this file + spark_write_partitioned.py into dags/.
"""

from datetime import datetime

from airflow.decorators import dag
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator


@dag(
    dag_id="spark_partitioned_data_v1",
    schedule="*/15 * * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["draft", "spark"],
)
def pipeline():

    SparkSubmitOperator(
        task_id="write_partitioned_data",
        conn_id="spark_default",
        application="/opt/airflow/dags/spark_write_partitioned.py",
        deploy_mode="client",
        verbose=True,
        # data_interval_start is the scheduled slot time — stable across reruns.
        # Jinja renders these before the operator submits the job.
        application_args=[
            "{{ data_interval_start | ds }}",               # ds  e.g. 2026-03-13
            "{{ data_interval_start.strftime('%H') }}",     # hr  e.g. 14
            "{{ data_interval_start.strftime('%M') }}",     # min e.g. 00 / 15 / 30 / 45
        ],
    )


pipeline()
