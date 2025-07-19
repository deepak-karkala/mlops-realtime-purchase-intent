import os
import json
import time
import boto3
from locust import User, task, between
from botocore.config import Config
import random

# --- Locust Configuration ---
AWS_REGION = "eu-west-1"
SAGEMAKER_ENDPOINT_NAME = os.environ.get("STAGING_SAGEMAKER_ENDPOINT")

class Boto3Client:
    """A wrapper for the Boto3 SageMaker client to be used in Locust."""
    def __init__(self, host=""):
        # Increase retries and timeouts for a production load test
        config = Config(
            retries={'max_attempts': 5, 'mode': 'standard'},
            connect_timeout=10,
            read_timeout=10
        )
        self.sagemaker_runtime = boto3.client(
            "sagemaker-runtime",
            region_name=AWS_REGION,
            config=config
        )

    def invoke_endpoint(self, payload):
        """Invoke endpoint and record the result in Locust."""
        request_meta = {
            "request_type": "sagemaker",
            "name": "invoke_endpoint",
            "start_time": time.time(),
            "response_length": 0,
            "response": None,
            "context": {},
            "exception": None,
        }
        start_perf_counter = time.perf_counter()
        
        try:
            response = self.sagemaker_runtime.invoke_endpoint(
                EndpointName=SAGEMAKER_ENDPOINT_NAME,
                ContentType='application/json',
                Body=payload
            )
            response_body = response['Body'].read()
            request_meta["response_length"] = len(response_body)
        except Exception as e:
            request_meta["exception"] = e
        
        request_meta["response_time"] = (time.perf_counter() - start_perf_counter) * 1000
        # This is where we fire the event for Locust to record
        events.request.fire(**request_meta)

class SageMakerUser(User):
    """
    Simulates a user making prediction requests to the SageMaker endpoint.
    """
    wait_time = between(0.1, 0.5) # Wait 100-500ms between requests
    
    def __init__(self, environment):
        super().__init__(environment)
        if SAGEMAKER_ENDPOINT_NAME is None:
            raise ValueError("STAGING_SAGEMAKER_ENDPOINT env var must be set for Locust test.")
        self.client = Boto3Client()

    @task
    def make_prediction(self):
        # Generate a random payload to simulate different users
        user_id = f"load-test-user-{random.randint(1, 10000)}"
        session_id = f"load-test-session-{random.randint(1, 50000)}"
        
        payload = json.dumps({
            "user_id": user_id,
            "session_id": session_id
        })
        
        self.client.invoke_endpoint(payload)

# Locust needs to be imported here for the event hook to work
from locust import events