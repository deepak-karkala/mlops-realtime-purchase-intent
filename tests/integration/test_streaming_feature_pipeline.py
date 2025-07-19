import os
import time
import json
import boto3
import pytest
from feast import FeatureStore

TEST_SESSION_ID = f"test-session-{int(time.time())}"
TEST_PRODUCT_ID = "prod-for-stream-test"

@pytest.mark.integration
def test_streaming_pipeline_end_to_end():
    """
    Pushes a synthetic event to the raw Kinesis stream and validates
    that the feature eventually appears in the Feast online store.
    """
    # --- 1. SETUP ---
    kinesis_client = boto3.client("kinesis", region_name="eu-west-1")
    raw_stream_name = "raw-events-stream"
    
    # --- 2. SEND EVENT ---
    event_payload = {
        "event_id": "evt-stream-test",
        "event_type": "add_to_cart",
        "product_id": TEST_PRODUCT_ID,
        "user_id": "user-stream-test",
        "session_id": TEST_SESSION_ID,
        "client_timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    kinesis_client.put_record(
        StreamName=raw_stream_name,
        Data=json.dumps(event_payload).encode('utf-8'),
        PartitionKey=TEST_SESSION_ID
    )
    logging.info(f"Sent test event for session {TEST_SESSION_ID} to Kinesis.")

    # --- 3. WAIT & POLL ---
    # Wait for the event to propagate through ingestion lambda and Spark streaming
    time.sleep(90) # This wait time depends on the streaming trigger interval

    # --- 4. VALIDATE in FEAST ---
    logging.info("Polling Feast online store for updated feature...")
    fs = FeatureStore(repo_path="feature_repo/")
    
    feature_vector = fs.get_online_features(
        features=["session_streaming_features:add_to_cart_count"],
        entity_rows=[{"session_id": TEST_SESSION_ID}],
    ).to_dict()

    logging.info(f"Retrieved feature vector: {feature_vector}")
    
    assert feature_vector["add_to_cart_count"][0] >= 1, \
        "Feature was not updated correctly in the online store!"