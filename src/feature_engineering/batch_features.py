import logging
from datetime import datetime
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, max, avg, count, datediff, lit, window
from pyspark.sql.types import StructType

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def compute_user_features(spark: SparkSession, silver_df: DataFrame) -> DataFrame:
    """Computes historical features for each user."""
    
    logging.info("Computing historical user features...")
    
    # Ensure all timestamps are handled correctly
    purchase_events = silver_df.filter(col("event_type") == "purchase")
    
    # Lifetime purchase count
    lifetime_purchases = purchase_events.groupBy("user_id").agg(
        count("event_id").alias("lifetime_purchase_count")
    )

    # Average order value over the last 90 days
    ninety_days_ago = datetime.utcnow() - timedelta(days=90)
    aov_90d = purchase_events.filter(col("event_timestamp") >= lit(ninety_days_ago))\
        .groupBy("user_id")\
        .agg(avg("price").alias("avg_order_value_90d"))

    # Days since last purchase
    days_since_purchase = purchase_events.groupBy("user_id").agg(
        max("event_timestamp").alias("last_purchase_ts")
    ).withColumn(
        "days_since_last_purchase",
        datediff(lit(datetime.utcnow()), col("last_purchase_ts"))
    )

    # Join all features together
    features_df = lifetime_purchases\
        .join(aov_90d, "user_id", "left")\
        .join(days_since_purchase.select("user_id", "days_since_last_purchase"), "user_id", "left")

    # Add other features like preferred_product_category
    # ... (logic elided for brevity) ...

    # Add timestamp columns required by Feast
    final_df = features_df.withColumn("event_timestamp", lit(datetime.utcnow()))\
                           .withColumn("created_timestamp", lit(datetime.utcnow()))
    
    logging.info("Finished computing user features.")
    return final_df

if __name__ == '__main__':
    # This block runs when the script is submitted to Spark
    
    # Get S3 paths from arguments passed by Airflow
    # For example: --silver-path s3://... --output-path s3://...
    
    spark = SparkSession.builder.appName("BatchFeatureEngineering").getOrCreate()
    
    # silver_df = spark.read.parquet(silver_path)
    # features_df = compute_user_features(spark, silver_df)
    # features_df.write.mode("overwrite").parquet(output_path)
    
    spark.stop()