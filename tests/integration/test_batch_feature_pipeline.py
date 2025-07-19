import os
import time
import logging
import pytest
from feast import FeatureStore
from airflow_client.client import Client
from airflow_client.client.api import dag_run_api
from airflow_client.client.model.dag_run import DAGRun
from airflow_client.client.model.error import Error
from pprint import pprint

# Configure logging
logging.basicConfig(level=logging.INFO)

# --- Test Configuration ---
# These would be fetched from environment variables in a CI/CD runner
AIRFLOW_HOST = os.environ.get("STAGING_AIRFLOW_HOST", "http://localhost:8080/api/v1")
AIRFLOW_USERNAME = os.environ.get("STAGING_AIRFLOW_USERNAME", "airflow")
AIRFLOW_PASSWORD = os.environ.get("STAGING_AIRFLOW_PASSWORD", "airflow")

DAG_ID = "batch_feature_engineering"
STAGING_FEAST_REPO_PATH = "feature_repo/"

# The specific user we will check for in the feature store after the pipeline runs
TEST_USER_ID = "user_for_integration_test" 
# The expected value for this user based on our sample data
EXPECTED_PURCHASE_COUNT = 5 

# --- Pytest Marker ---
@pytest.mark.integration
def test_batch_feature_pipeline_end_to_end():
    """
    Triggers the batch feature engineering DAG in a staging environment and
    validates that the final feature values are correctly written to the
    online feature store.
    """
    # --- 1. SETUP: Initialize API clients ---
    api_client = Client(host=AIRFLOW_HOST, user=AIRFLOW_USERNAME, passwd=AIRFLOW_PASSWORD)
    
    # --- 2. TRIGGER: Start a new DAG Run ---
    logging.info(f"Triggering DAG: {DAG_ID}")
    dag_run_api_instance = dag_run_api.DAGRunApi(api_client)
    
    try:
        # Trigger the DAG with a specific conf to override the default paths
        # This points the job to our small, static test dataset
        api_response = dag_run_api_instance.post_dag_run(
            dag_id=DAG_ID,
            dag_run=DAGRun(
                conf={
                    "input_path": "s3://ecom-propensity-staging-data/sample_silver_data.parquet",
                    "output_path": f"s3://ecom-propensity-staging-gold/test_run_{int(time.time())}/"
                }
            )
        )
        dag_run_id = api_response.dag_run_id
        logging.info(f"Successfully triggered DAG run with ID: {dag_run_id}")
    except Exception as e:
        pytest.fail(f"Failed to trigger DAG run: {e}")

    # --- 3. POLL: Wait for the DAG Run to complete ---
    wait_for_dag_run_completion(api_client, dag_run_id)

    # --- 4. VALIDATE: Check the final state in the Feature Store ---
    logging.info("DAG run complete. Validating results in Feast online store...")
    fs = FeatureStore(repo_path=STAGING_FEAST_REPO_PATH)
    
    feature_vector = fs.get_online_features(
        features=[
            "user_historical_features:lifetime_purchase_count",
        ],
        entity_rows=[{"user_id": TEST_USER_ID}],
    ).to_dict()

    logging.info(f"Retrieved feature vector: {feature_vector}")

    # Assert that the feature was updated with the correct value
    assert feature_vector["lifetime_purchase_count"][0] == EXPECTED_PURCHASE_COUNT, \
        f"Feature validation failed for user {TEST_USER_ID}!"
    
    logging.info("Integration test passed successfully!")


def wait_for_dag_run_completion(api_client: Client, dag_run_id: str, timeout_seconds: int = 600):
    """Polls the Airflow API until the DAG run is complete or timeout is reached."""
    dag_run_api_instance = dag_run_api.DAGRunApi(api_client)
    start_time = time.time()
    
    while time.time() - start_time < timeout_seconds:
        try:
            api_response = dag_run_api_instance.get_dag_run(dag_id=DAG_ID, dag_run_id=dag_run_id)
            state = api_response.state
            logging.info(f"Polling DAG run {dag_run_id}. Current state: {state}")
            
            if state == "success":
                return
            elif state == "failed":
                pytest.fail(f"DAG run {dag_run_id} failed.")
            
            time.sleep(30) # Wait 30 seconds between polls
        except Exception as e:
            pytest.fail(f"API error while polling for DAG run status: {e}")
            
    pytest.fail(f"Timeout: DAG run {dag_run_id} did not complete within {timeout_seconds} seconds.")
