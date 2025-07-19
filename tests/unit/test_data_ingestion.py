import json
import base64
from unittest.mock import patch, MagicMock
import pytest

# Add src to path to allow imports
import sys
sys.path.append('src/data_ingestion')

from app import lambda_handler
from schemas import ProcessedEvent

# Mock a valid Kinesis event record
def create_mock_record(payload: dict) -> dict:
    return {
        'kinesis': {
            'data': base64.b64encode(json.dumps(payload).encode('utf-8'))
        }
    }

@pytest.fixture
def valid_event_payload():
    return {
        "event_id": "evt-123",
        "event_type": "page_view",
        "product_id": "prod-abc",
        "user_id": "user-xyz",
        "session_id": "sess-456",
        "client_timestamp": "2023-10-27T10:00:00Z"
    }

@patch('app.kinesis_client')
def test_lambda_handler_success(mock_kinesis_client, valid_event_payload):
    """Test the happy path: a valid record is processed and sent."""
    mock_kinesis_client.put_records.return_value = {'FailedRecordCount': 0}
    
    mock_event = {'Records': [create_mock_record(valid_event_payload)]}
    
    result = lambda_handler(mock_event, {})
    
    assert result['status'] == 'OK'
    assert result['records_processed'] == 1
    mock_kinesis_client.put_records.assert_called_once()
    
    # Check that the data sent to Kinesis is a valid ProcessedEvent
    call_args = mock_kinesis_client.put_records.call_args[1]
    sent_record_data = call_args['Records'][0]['Data']
    processed_event_dict = json.loads(sent_record_data)
    
    # This will raise ValidationError if the schema is wrong
    ProcessedEvent(**processed_event_dict)
    assert processed_event_dict['session_id'] == valid_event_payload['session_id']

@patch('app.kinesis_client')
def test_lambda_handler_validation_error(mock_kinesis_client):
    """Test that a record with missing required fields is skipped."""
    invalid_payload = {"event_id": "evt-bad"} # Missing fields
    mock_event = {'Records': [create_mock_record(invalid_payload)]}
    
    result = lambda_handler(mock_event, {})
    
    assert result['status'] == 'OK'
    assert result['records_processed'] == 0
    mock_kinesis_client.put_records.assert_not_called()

@patch('app.kinesis_client')
def test_lambda_handler_kinesis_failure(mock_kinesis_client, valid_event_payload):
    """Test that an exception is raised if the kinesis call fails."""
    mock_kinesis_client.put_records.side_effect = Exception("AWS Error")
    mock_event = {'Records': [create_mock_record(valid_event_payload)]}
    
    with pytest.raises(Exception, match="AWS Error"):
        lambda_handler(mock_event, {})