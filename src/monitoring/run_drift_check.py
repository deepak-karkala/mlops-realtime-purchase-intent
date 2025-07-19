import sys
import argparse
import logging
import pandas as pd
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, TargetDriftPreset

logging.basicConfig(level=logging.INFO, format="%(asctime)-15s %(message)s")
logger = logging.getLogger()

def run_drift_analysis(ref_data_path: str, prod_data_path: str, report_path: str):
    """
    Compares production data to reference data to detect drift.
    Exits with a non-zero status code if drift is detected.
    """
    logger.info("Loading reference data from %s", ref_data_path)
    ref_df = pd.read_parquet(ref_data_path)
    
    logger.info("Loading production data from %s", prod_data_path)
    prod_df = pd.read_parquet(prod_data_path)

    # For this example, let's assume prediction is 'propensity' and target is 'converted'
    ref_df.rename(columns={'target': 'converted'}, inplace=True)

    logger.info("Generating data drift report...")
    report = Report(metrics=[
        DataDriftPreset(),
        TargetDriftPreset(),
    ])
    report.run(reference_data=ref_df, current_data=prod_df)
    
    logger.info("Saving drift report to %s", report_path)
    report.save_html(report_path)

    drift_report = report.as_dict()
    is_drift_detected = drift_report['metrics'][0]['result']['dataset_drift']
    
    if is_drift_detected:
        logger.error("Data drift detected! The production data distribution has shifted significantly.")
        sys.exit(1) # Fail the task if drift is found
    else:
        logger.info("No significant data drift detected.")
        sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref-data", required=True)
    parser.add_argument("--prod-data", required=True)
    parser.add_argument("--report-path", required=True)
    args = parser.parse_args()
    run_drift_analysis(args.ref_data, args.prod_data, args.report_path)