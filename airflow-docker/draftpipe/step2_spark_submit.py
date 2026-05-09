"""
STEP 2 — Submit a PySpark job via SparkSubmitOperator.

New concepts:
  - SparkSubmitOperator : Airflow operator that runs spark-submit and waits
    for the job to finish (pass/fail).
  - conn_id            : Spark connection. Already wired via env var in
    docker-compose: AIRFLOW_CONN_SPARK_DEFAULT=spark://spark-master:7077
  - application        : path to the PySpark script inside the Airflow worker
    container. The dags/ folder is mounted at /opt/airflow/dags.
  - deploy_mode=cluster : driver runs on the Spark master, not on the Airflow
    worker. spark-defaults.conf (already mounted in Spark containers) handles
    all JAR/catalog config — nothing extra needed here.
  - verbose=True       : streams spark-submit stdout into the Airflow task log.

To promote: copy this file + spark_write_static.py into dags/.
"""

from datetime import datetime

from airflow.decorators import dag
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator


@dag(
    dag_id="spark_static_data_v2_submit",
    schedule="*/15 * * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["draft", "spark"],
)
def pipeline():

    SparkSubmitOperator(
        task_id="write_static_data",
        conn_id="spark_default",
        application="/opt/airflow/dags/spark_write_static.py",
        deploy_mode="client",   # driver runs on Spark master; jars/catalog from spark-defaults.conf
        verbose=True,
    )


pipeline()
