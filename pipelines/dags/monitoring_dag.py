from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago

def on_drift_detection_failure(context):
    """
    This function is called when the drift check fails.
    It triggers the GitHub Actions workflow for retraining.
    """
    # In a real system, you'd use a more robust method like calling the GitHub API
    # from a PythonOperator. For clarity, a curl command is shown.
    # The GITHUB_TOKEN would be stored as an Airflow secret.
    trigger_workflow_command = """
    curl -X POST \
      -H "Accept: application/vnd.github.v3+json" \
      -H "Authorization: token {{ conn.github_pat.password }}" \
      https://api.github.com/repos/your-org/ecom-propensity/actions/workflows/retrain_and_deploy.yml/dispatches \
      -d '{"ref":"main", "inputs":{"trigger_reason":"data_drift"}}'
    """
    return BashOperator(
        task_id='trigger_retraining_workflow',
        bash_command=trigger_workflow_command,
    ).execute(context=context)

with DAG(
    dag_id='daily_monitoring_and_drift_check',
    start_date=days_ago(1),
    schedule_interval='@daily',
    catchup=False,
    tags=['monitoring'],
) as dag:
    
    run_drift_check = BashOperator(
        task_id='run_drift_check',
        bash_command=(
            "python /opt/airflow/src/monitoring/run_drift_check.py "
            "--ref-data s3://ecom-propensity-gold-features/training_data_profile.parquet "
            "--prod-data s3://ecom-propensity-monitoring-logs/latest/ "
            "--report-path /tmp/drift_report_{{ ds }}.html"
        ),
        on_failure_callback=on_drift_detection_failure,
    )