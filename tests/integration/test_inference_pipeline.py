import os
import json
import boto3
import pytest

SAGEMAKER_ENDPOINT_NAME = os.environ.get("STAGING_SAGEMAKER_ENDPOINT")

@pytest.mark.integration
def test_sagemaker_endpoint_invocation():
    """Sends a real request to the deployed SageMaker endpoint."""
    assert SAGEMAKER_ENDPOINT_NAME is not None, "STAGING_SAGEMAKER_ENDPOINT env var not set"

    sagemaker_runtime = boto3.client("sagemaker-runtime", region_name="eu-west-1")
    
    payload = {
        "user_id": "integration-test-user",
        "session_id": "integration-test-session"
    }
    
    response = sagemaker_runtime.invoke_endpoint(
        EndpointName=SAGEMAKER_ENDPOINT_NAME,
        ContentType='application/json',
        Body=json.dumps(payload)
    )
    
    assert response['ResponseMetadata']['HTTPStatusCode'] == 200
    
    result = json.loads(response['Body'].read().decode())
    assert 'propensity' in result
    assert isinstance(result['propensity'], float)```
