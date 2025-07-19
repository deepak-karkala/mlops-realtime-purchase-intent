from google.protobuf.duration_pb2 import Duration
from feast import Entity, FeatureView, Field, FileSource
from feast.types import Float32, Int64, String

# Define the user entity
user = Entity(name="user_id", join_keys=["user_id"])

# Define the source of our batch features
# This points to the S3 "Gold" bucket where our Spark job will write its output
batch_feature_source = FileSource(
    path="s3://ecom-propensity-gold-features/user_features/",
    event_timestamp_column="event_timestamp",
    created_timestamp_column="created_timestamp",
)

# Define the Feature View for user-level historical features
user_features_view = FeatureView(
    name="user_historical_features",
    entities=[user],
    ttl=Duration(seconds=86400 * 90),  # 90 days
    schema=[
        Field(name="lifetime_purchase_count", dtype=Int64),
        Field(name="avg_order_value_90d", dtype=Float32),
        Field(name="days_since_last_purchase", dtype=Int64),
        Field(name="preferred_product_category", dtype=String),
    ],
    online=True,
    source=batch_feature_source,
    tags={"owner": "ml_team", "pipeline": "batch"},
)