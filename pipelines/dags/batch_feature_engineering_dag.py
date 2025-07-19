from airflow import DAG
from airflow.providers.amazon.aws.operators.emr import EmrCreateJobFlowOperator, EmrAddStepsOperator, EmrTerminateJobFlowOperator
from airflow.providers.great_expectations.operators.great_expectations import GreatExpectationsOperator
from airflow.operators.bash import BashOperator
from datetime import datetime

# Define the Spark step for EMR
spark_steps = [
    {
        "Name": "ComputeBatchFeatures",
        "ActionOnFailure": "TERMINATE_CLUSTER",
        "HadoopJarStep": {
            "Jar": "command-runner.jar",
            "Args": [
                "spark-submit",
                "--deploy-mode", "cluster",
                "s3://ecom-propensity-airflow-artifacts/scripts/batch_features.py",
                "--silver-path", "s3://ecom-propensity-silver/...",
                "--output-path", "s3://ecom-propensity-gold-features/user_features_temp/"
            ],
        },
    }
]

# Define the EMR cluster configuration
job_flow_overrides = {
    "Name": "ecom-propensity-batch-feature-emr",
    "ReleaseLabel": "emr-6.9.0",
    "Applications": [{"Name": "Spark"}],
    "Instances": {
        "InstanceGroups": [
            {"Name": "Master nodes", "Market": "ON_DEMAND", "InstanceRole": "MASTER", "InstanceType": "m5.xlarge", "InstanceCount": 1},
            {"Name": "Core nodes", "Market": "ON_DEMAND", "InstanceRole": "CORE", "InstanceType": "m5.xlarge", "InstanceCount": 2},
        ],
        "KeepJobFlowAliveWhenNoSteps": False,
        "TerminationProtected": False,
    },
    "VisibleToAllUsers": True,
    "JobFlowRole": "EMR_EC2_DefaultRole",
    "ServiceRole": "EMR_DefaultRole",
}

with DAG(
    dag_id='batch_feature_engineering',
    start_date=datetime(2023, 1, 1),
    schedule_interval='@daily',
    catchup=False,
    tags=['feature-engineering'],
) as dag:

    # 1. Create a transient EMR cluster
    cluster_creator = EmrCreateJobFlowOperator(
        task_id="create_emr_cluster",
        job_flow_overrides=job_flow_overrides,
        aws_conn_id="aws_default",
        emr_conn_id="emr_default",
    )

    # 2. Add the Spark job step
    step_adder = EmrAddStepsOperator(
        task_id="run_spark_job",
        job_flow_id="{{ task_instance.xcom_pull(task_ids='create_emr_cluster', key='return_value') }}",
        steps=spark_steps,
    )

    # 3. Validate the output data
    data_validator = GreatExpectationsOperator(
        task_id="validate_features",
        expectation_suite_name="user_features.warning", # Example suite
        data_context_root_dir="/usr/local/airflow/great_expectations",
        data_asset_name="s3://ecom-propensity-gold-features/user_features_temp/"
    )
    
    # 4. Materialize features to the online store
    feast_materialize = BashOperator(
        task_id="feast_materialize",
        bash_command="cd /usr/local/airflow/feature_repo && feast materialize-incremental $(date -u +'%Y-%m-%dT%H:%M:%SZ')",
    )

    # 5. Terminate the EMR cluster
    cluster_remover = EmrTerminateJobFlowOperator(
        task_id="terminate_emr_cluster",
        job_flow_id="{{ task_instance.xcom_pull(task_ids='create_emr_cluster', key='return_value') }}",
        trigger_rule="all_done", # Run whether previous steps succeed or fail
    )
    
    # Define dependencies
    cluster_creator >> step_adder >> data_validator >> feast_materialize >> cluster_remover