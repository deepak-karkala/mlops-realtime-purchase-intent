import pytest
from pyspark.sql import SparkSession
from datetime import datetime, timedelta

# Add src to path to allow imports
import sys
sys.path.append('src/feature_engineering')

from batch_features import compute_user_features

@pytest.fixture(scope="session")
def spark_session():
    """Creates a Spark session for testing."""
    return SparkSession.builder.master("local[2]").appName("PytestSpark").getOrCreate()

def test_compute_user_features(spark_session):
    """Test the feature computation logic with sample data."""
    # Create sample data representing events
    utc_now = datetime.utcnow()
    yesterday_utc = utc_now - timedelta(days=1)
    
    # User 1: One purchase yesterday
    # User 2: Two purchases, one today, one 100 days ago
    mock_data = [
        ("evt1", "purchase", "user1", "prodA", 10.0, yesterday_utc),
        ("evt2", "purchase", "user2", "prodB", 20.0, utc_now),
        ("evt3", "purchase", "user2", "prodC", 30.0, utc_now - timedelta(days=100)),
        ("evt4", "page_view", "user1", "prodB", None, utc_now),
    ]
    schema = ["event_id", "event_type", "user_id", "product_id", "price", "event_timestamp"]
    silver_df = spark_session.createDataFrame(mock_data, schema)
    
    # Compute features
    features_df = compute_user_features(spark_session, silver_df)
    features_map = {row['user_id']: row for row in features_df.collect()}
    
    # Assertions for User 1
    assert features_map['user1']['lifetime_purchase_count'] == 1
    assert features_map['user1']['days_since_last_purchase'] == 1
    
    # Assertions for User 2
    assert features_map['user2']['lifetime_purchase_count'] == 2
    # Only the recent purchase is in the 90-day window
    assert features_map['user2']['avg_order_value_90d'] == 20.0
    assert features_map['user2']['days_since_last_purchase'] == 0