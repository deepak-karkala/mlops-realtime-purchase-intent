from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.providers.amazon.aws.operators.sagemaker import SageMakerTrainingOperator
from airflow.utils.dates import days_ago
from sagemaker.estimator import Estimator

# --- DAG Definition ---
with DAG(
    dag_id='model_training_pipeline',
    start_date=days_ago(1),
    schedule_interval='@weekly',
    catchup=False,
    tags=['training'],
) as dag:

    # Task 1: Get data from Feast
    def get_data_from_feast(**kwargs):
        # ... logic from src/model_training/data.py
        # Saves data to S3 and pushes path via XCom
        pass

    # Task 2: Validate data with Great Expectations
    def validate_data(**kwargs):
        # ... logic from src/model_training/validate.py
        pass

    # Task 3: Launch SageMaker Training Job
    # Define the estimator here for clarity
    sagemaker_estimator = Estimator(
        image_uri="<aws_account_id>.dkr.ecr.eu-west-1.amazonaws.com/ecom-propensity/training:latest",
        role="arn:aws:iam::<aws_account_id>:role/sagemaker-training-execution-role",
        instance_count=1,
        instance_type='ml.m5.large',
        # Pass hyperparameters
        hyperparameters={'n_estimators': 250, 'learning_rate': 0.05},
        # Pass environment variables
        environment={'MLFLOW_TRACKING_URI': 'http://your-mlflow-server:5000'}
    )
    
    train_model = SageMakerTrainingOperator(
        task_id='train_model',
        config={
            "TrainingJobName": "propensity-model-{{ ds_nodash }}",
            "AlgorithmSpecification": {
                "TrainingImage": sagemaker_estimator.image_uri,
                "TrainingInputMode": "File",
            },
            "RoleArn": sagemaker_estimator.role,
            # ... other SageMaker configs
        },
        inputs={'train': '{{ ti.xcom_pull(task_ids="get_data_task")["s3_path"] }}'}
    )

    # Task 4: Evaluate model and decide whether to proceed
    def evaluate_and_decide(**kwargs):
        # ... logic from src/model_training/evaluate.py
        # Compares new model run to prod model in MLflow Registry
        # if is_better:
        #    return 'run_advanced_tests'
        # else:
        #    return 'end_pipeline'
        pass
    
    branch_on_evaluation = BranchPythonOperator(
        task_id='check_evaluation',
        python_callable=evaluate_and_decide,
    )

    # Task 5: Run advanced behavioral and fairness tests
    def run_advanced_tests(**kwargs):
        # ... logic from src/model_training/test.py
        pass

    # Task 6: Register model in MLflow Staging
    def register_model(**kwargs):
        # ... logic from src/model_training/register.py
        pass

    # Define dependencies
    # get_data_task >> validate_data >> train_model >> branch_on_evaluation
    # branch_on_evaluation >> [run_advanced_tests_task, end_pipeline_task]
    # run_advanced_tests_task >> register_model_task