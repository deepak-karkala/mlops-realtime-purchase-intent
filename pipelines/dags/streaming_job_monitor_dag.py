from airflow import DAG
from airflow.providers.amazon.aws.sensors.emr import EmrClusterSensor
from airflow.providers.slack.operators.slack_webhook import SlackWebhookOperator
from datetime import datetime

STREAMING_CLUSTER_ID = "j-STREAMINGCLUSTERID" # This should come from a Variable or SSM

def slack_alert_on_failure(context):
    """Send a Slack alert if the task fails."""
    alert = SlackWebhookOperator(
        task_id='slack_alert',
        http_conn_id='slack_connection', # Airflow connection to Slack webhook
        message=f"""
            :red_circle: High-Priority Alert: EMR Streaming Cluster is DOWN!
            *DAG*: {context.get('task_instance').dag_id}
            *Task*: {context.get('task_instance').task_id}
            *Cluster ID*: {STREAMING_CLUSTER_ID}
        """,
        channel='#mlops-alerts'
    )
    return alert.execute(context=context)

with DAG(
    dag_id='streaming_job_monitor',
    start_date=datetime(2023, 1, 1),
    schedule_interval='*/15 * * * *', # Run every 15 minutes
    catchup=False,
    on_failure_callback=slack_alert_on_failure,
    tags=['monitoring', 'streaming'],
) as dag:
    
    check_emr_cluster_health = EmrClusterSensor(
        task_id='check_emr_cluster_health',
        job_flow_id=STREAMING_CLUSTER_ID,
        target_states=['WAITING'], # 'WAITING' means the cluster is idle and ready for steps
        aws_conn_id='aws_default',
    )