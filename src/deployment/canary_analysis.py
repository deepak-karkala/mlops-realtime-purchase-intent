import sys
import argparse
import logging
from datetime import datetime, timedelta
import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)-15s %(message)s")
logger = logging.getLogger()

# Define acceptable performance thresholds for the challenger
MAX_LATENCY_INCREASE_FACTOR = 1.10  # Allow 10% higher latency
MAX_ERROR_RATE_ABSOLUTE = 0.01      # Max 1% error rate

def analyze_canary_metrics(endpoint_name: str, bake_time_mins: int) -> bool:
    """
    Queries CloudWatch metrics for champion and challenger variants and compares them.
    Returns True if the challenger is healthy, False otherwise.
    """
    client = boto3.client("cloudwatch", region_name="eu-west-1")
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=bake_time_mins)
    
    def get_metric(variant_name, metric_name):
        response = client.get_metric_data(
            MetricDataQueries=[{
                'Id': 'm1',
                'MetricStat': {
                    'Metric': {'Namespace': 'AWS/SageMaker', 'MetricName': metric_name,
                               'Dimensions': [{'Name': 'EndpointName', 'Value': endpoint_name},
                                              {'Name': 'VariantName', 'Value': variant_name}]},
                    'Period': 60, 'Stat': 'Average'
                }, 'ReturnData': True
            }],
            StartTime=start_time, EndTime=end_time
        )
        values = response['MetricDataResults'][0]['Values']
        return values[0] if values else 0.0

    # --- Fetch metrics for both variants ---
    champion_latency = get_metric("champion", "ModelLatency")
    challenger_latency = get_metric("challenger", "ModelLatency")
    challenger_errors = get_metric("challenger", "Invocation5XXErrors")
    
    logger.info(f"Champion Latency: {champion_latency:.2f}ms")
    logger.info(f"Challenger Latency: {challenger_latency:.2f}ms")
    logger.info(f"Challenger Errors (avg per min): {challenger_errors}")

    # --- Compare against thresholds ---
    healthy = True
    if challenger_latency > champion_latency * MAX_LATENCY_INCREASE_FACTOR:
        logger.error("FAIL: Challenger latency is unacceptably high.")
        healthy = False
    if challenger_errors > MAX_ERROR_RATE_ABSOLUTE:
        logger.error("FAIL: Challenger error rate is unacceptably high.")
        healthy = False

    if healthy:
        logger.info("SUCCESS: Challenger performance is within acceptable limits.")
    
    return healthy

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint-name", required=True)
    parser.add_argument("--bake-time-mins", type=int, default=15)
    args = parser.parse_args()
    
    if not analyze_canary_metrics(args.endpoint_name, args.bake_time_mins):
        sys.exit(1)
    sys.exit(0)