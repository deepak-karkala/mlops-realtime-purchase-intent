import os
import json
import time
import boto3
import pytest
from pydantic import BaseModel, ValidationError

# --- Test Configuration ---
SAGEMAKER_ENDPOINT_NAME = os.environ.get("STAGING_SAGEMAKER_ENDPOINT")
AWS_REGION = "eu-west-1"

# --- Pydantic Model for Response Validation ---
# This defines the "API Contract" we expect.
class ExpectedResponse(BaseModel):
    propensity: float
    model_version: str

# --- Pytest Fixtures ---
@pytest.fixture(scope="module")
def sagemaker_client():
    """Boto3 client for SageMaker service."""
    return boto3.client("sagemaker", region_name=AWS_REGION)

@pytest.fixture(scope="module")
def sagemaker_runtime_client():
    """Boto3 client for SageMaker runtime (invocations)."""
    return boto3.client("sagemaker-runtime", region_name=AWS_REGION)

# --- Test Cases ---
@pytest.mark.smoke
@pytest.mark.integration
def test_endpoint_is_in_service(sagemaker_client):
    """
    Smoke Test 1: Checks that the endpoint is deployed and healthy.
    This is our proxy for the /health check.
    """
    assert SAGEMAKER_ENDPOINT_NAME is not None, "STAGING_SAGEMAKER_ENDPOINT env var not set"
    
    try:
        response = sagemaker_client.describe_endpoint(EndpointName=SAGEMAKER_ENDPOINT_NAME)
        status = response["EndpointStatus"]
        assert status == "InService", f"Endpoint is not InService. Current status: {status}"
        
        # We can add a wait loop here if needed
        # ...
        
    except sagemaker_client.exceptions.ClientError as e:
        pytest.fail(f"Could not describe SageMaker endpoint. Error: {e}")

@pytest.mark.smoke
@pytest.mark.integration
def test_api_contract_and_schema(sagemaker_runtime_client):
    """
    Smoke Test 2: Invokes the endpoint and validates the response schema (API Contract).
    """
    payload = {
        "user_id": "contract-test-user",
        "session_id": "contract-test-session"
    }
    
    response = sagemaker_runtime_client.invoke_endpoint(
        EndpointName=SAGEMAKER_ENDPOINT_NAME,
        ContentType='application/json',
        Body=json.dumps(payload)
    )
    
    assert response['ResponseMetadata']['HTTPStatusCode'] == 200
    
    # Validate the response body against our Pydantic schema
    response_body = json.loads(response['Body'].read().decode())
    try:
        validated_response = ExpectedResponse(**response_body)
        assert 0.0 <= validated_response.propensity <= 1.0
    except ValidationError as e:
        pytest.fail(f"API contract validation failed. Response did not match schema: {e}")