from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

with DAG(
    dag_id='ab_test_analysis',
    start_date=datetime(2023, 1, 1),
    schedule_interval=None, # Triggered manually
    catchup=False,
    tags=['analysis', 'ab-testing'],
) as dag:
    
    run_analysis = BashOperator(
        task_id='run_statistical_analysis',
        bash_command=(
            "python /opt/airflow/src/analysis/run_ab_test_analysis.py "
            "--data-path s3://ecom-propensity-analytics/ab-test-results/experiment_XYZ.parquet"
        )
    )