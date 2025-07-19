import os
import time
import pytest
from airflow_client.client import Client
import mlflow

# --- Test Configuration ---
DAG_ID = "model_training_pipeline"
MLFLOW_TRACKING_URI = os.environ.get("STAGING_MLFLOW_URI")

@pytest.mark.integration
def test_training_pipeline_end_to_end():
    """Triggers the training DAG and validates that a new model version is created in Staging."""
    
    # --- 1. SETUP: Get current latest version ---
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    client = mlflow.tracking.MlflowClient()
    model_name = "PurchasePropensityModel"
    try:
        initial_versions = client.get_latest_versions(model_name, stages=["Staging"])
        initial_version_count = len(initial_versions)
    except mlflow.exceptions.RestException:
        initial_version_count = 0 # Model doesn't exist yet

    # --- 2. TRIGGER: Start a new DAG Run ---
    # (Code to trigger DAG via Airflow API, similar to feature pipeline test)
    # ...
    
    # --- 3. POLL: Wait for the DAG Run to complete ---
    # (Code to poll for DAG run completion)
    # ...
    
    # --- 4. VALIDATE: Check MLflow Model Registry ---
    final_versions = client.get_latest_versions(model_name, stages=["Staging"])
    final_version_count = len(final_versions)

    assert final_version_count > initial_version_count, \
        "Integration test failed: No new model version was moved to Staging."