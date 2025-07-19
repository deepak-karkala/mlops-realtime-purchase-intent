import logging
import json
from datetime import datetime
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import StructType, StructField, StringType, TimestampType, IntegerType

import redis
from feast import FeatureStore

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Schema for the incoming JSON data from Kinesis
EVENT_SCHEMA = StructType([
    StructField("event_type", StringType()),
    Field("product_id", StringType()),
    Field("session_id", StringType(), False), # session_id is required
    Field("event_timestamp", TimestampType()),
    # ... other fields
])

def update_session_state(session_id, new_events, state):
    """The core stateful logic for updating session features."""
    
    # Get current state or initialize a new one
    if state.exists:
        current_state = state.get
    else:
        current_state = {
            "session_start_time": datetime.utcnow(),
            "distinct_products_viewed": set(),
            "add_to_cart_count": 0
        }

    # Iterate through new events and update state
    for event in new_events:
        if event.product_id:
            current_state["distinct_products_viewed"].add(event.product_id)
        if event.event_type == 'add_to_cart':
            current_state["add_to_cart_count"] += 1

    # Update state object and set a timeout to prevent infinite state growth
    state.update(current_state)
    state.setTimeoutDuration("24 hours") # Evict state if no events for 24 hours

    # Yield the updated features
    yield (session_id, 
           (datetime.utcnow() - current_state["session_start_time"]).seconds, 
           len(current_state["distinct_products_viewed"]), 
           current_state["add_to_cart_count"],
           datetime.utcnow())

def write_to_feast_online_store(df: DataFrame, epoch_id: int):
    """Writes a micro-batch of features to the Feast Redis store."""
    logging.info(f"Writing batch {epoch_id} to online store...")
    
    # Using feast's push mechanism is one way, another is direct to Redis
    # For performance, direct Redis client is often better.
    # Note: Connection pooling should be used in a real production job.
    r = redis.Redis(host='redis-endpoint', port=6379, db=0)
    
    for row in df.rdd.collect():
        entity_key = f"session_id:{row.session_id}"
        feature_payload = {
            "session_duration_seconds": row.session_duration_seconds,
            "distinct_products_viewed_count": row.distinct_products_viewed_count,
            "add_to_cart_count": row.add_to_cart_count
        }
        # In Redis, features are often stored in a Hash
        r.hset(entity_key, mapping=feature_payload)
    logging.info(f"Finished writing batch {epoch_id}.")


if __name__ == '__main__':
    spark = SparkSession.builder.appName("StreamingFeatureEngineering").getOrCreate()

    # Read from Kinesis
    kinesis_df = spark.readStream \
        .format("kinesis") \
        .option("streamName", "processed-events-stream") \
        .option("startingPosition", "latest") \
        .load()

    # Parse JSON data and apply schema
    json_df = kinesis_df.selectExpr("CAST(data AS STRING) as json") \
        .select(from_json(col("json"), EVENT_SCHEMA).alias("data")) \
        .select("data.*")

    # Apply the stateful transformation
    features_df = json_df.groupBy("session_id").flatMapGroupsWithState(
        outputMode="update",
        stateFormatVersion="2",
        timeoutConf="eventTimeTimeout",
        func=update_session_state
    ).toDF(["session_id", "session_duration_seconds", "distinct_products_viewed_count", "add_to_cart_count", "event_timestamp"])

    # --- Write to Sinks ---
    # Sink 1: Write to Feast Online Store (Redis)
    query_online = features_df.writeStream \
        .foreachBatch(write_to_feast_online_store) \
        .option("checkpointLocation", "s3://ecom-propensity-checkpoints/online_sink") \
        .start()

    # Sink 2: Write to S3 for Feast Offline Store (Archival)
    query_offline = features_df.writeStream \
        .format("parquet") \
        .outputMode("append") \
        .option("path", "s3://ecom-propensity-gold-features/session_features/") \
        .option("checkpointLocation", "s3://ecom-propensity-checkpoints/offline_sink") \
        .start()

    spark.streams.awaitAnyTermination()