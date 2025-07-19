from google.protobuf.duration_pb2 import Duration
from feast import Entity, FeatureView, Field, FileSource, ValueType

# Define session as an entity (can be joined with user_id)
session = Entity(name="session_id", value_type=ValueType.STRING)

# The source for these features is the PARQUET data being archived to S3
# by the streaming job. This is what Feast uses for creating training data.
stream_feature_source = FileSource(
    path="s3://ecom-propensity-gold-features/session_features/",
    event_timestamp_column="event_timestamp",
)

# Define the Feature View for real-time session features
session_features_view = FeatureView(
    name="session_streaming_features",
    entities=[session],
    ttl=Duration(seconds=86400 * 2),  # 2 days
    schema=[
        Field(name="session_duration_seconds", dtype=Int64),
        Field(name="distinct_products_viewed_count", dtype=Int64),
        Field(name="add_to_cart_count", dtype=Int64),
    ],
    online=True,
    source=stream_feature_source,
    tags={"owner": "ml_team", "pipeline": "streaming"},
)