#### **`/src/data_ingestion/app.py`**
```python
import os
import json
import base64
import logging
from typing import List, Dict

import boto3
from pydantic import ValidationError

from schemas import RawClickstreamEvent, ProcessedEvent

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize boto3 clients outside the handler for reuse
kinesis_client = boto3.client('kinesis')

PROCESSED_STREAM_NAME = os.environ.get("PROCESSED_STREAM_NAME", "processed-events-stream")

def lambda_handler(event, context):
    """
    Consumes a batch of records from the 'raw-events' Kinesis stream,
    validates, enriches them, and pushes them to the 'processed-events' stream.
    """
    processed_records: List[Dict] = []
    
    for record in event['Records']:
        try:
            # Kinesis records are base64 encoded
            payload_bytes = base64.b64decode(record['kinesis']['data'])
            payload_dict = json.loads(payload_bytes)
            
            # 1. Validate raw event against the Pydantic schema
            raw_event = RawClickstreamEvent(**payload_dict)
            
            # 2. Enrich the event
            processed_event = ProcessedEvent(**raw_event.dict())
            
            # Prepare for sending to the downstream Kinesis stream
            processed_records.append({
                'Data': processed_event.json().encode('utf-8'),
                'PartitionKey': processed_event.session_id # Use session_id to group events
            })
            
        except ValidationError as e:
            logger.error(f"Schema validation failed: {e}. Record: {record.get('kinesis', {})}")
            # In a production system, send malformed records to a Dead Letter Queue (DLQ)
            continue
        except (TypeError, json.JSONDecodeError) as e:
            logger.error(f"Failed to decode or parse JSON: {e}. Record: {record.get('kinesis', {})}")
            continue

    if not processed_records:
        logger.info("No valid records to process.")
        return {'status': 'OK', 'records_processed': 0}

    # 3. Push the enriched records to the processed stream in a batch
    try:
        put_records_response = kinesis_client.put_records(
            StreamName=PROCESSED_STREAM_NAME,
            Records=processed_records
        )
        logger.info(f"Successfully processed and sent {len(processed_records)} records downstream.")
        
        # You can add logic here to handle and retry failed records from the batch
        if put_records_response.get('FailedRecordCount', 0) > 0:
            logger.warning(f"Failed to send {put_records_response['FailedRecordCount']} records.")

    except Exception as e:
        logger.critical(f"Fatal error sending records to Kinesis: {e}")
        # Re-raise the exception to have Lambda retry the entire batch
        raise e
        
    return {
        'status': 'OK',
        'records_processed': len(processed_records)
    }