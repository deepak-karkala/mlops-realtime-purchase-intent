import sys
import argparse
import logging
import pandas as pd
import numpy as np
import mlflow

logging.basicConfig(level=logging.INFO, format="%(asctime)-15s %(message)s")
logger = logging.getLogger()

def run_sliced_evaluation(model, X_test: pd.DataFrame, y_test: pd.Series, overall_auc: float) -> bool:
    """Evaluates model performance on critical data slices."""
    logger.info("--- Running Sliced Evaluation ---")
    
    slices = {
        "mobile_users": "device_type_mobile == 1",
        "desktop_users": "device_type_desktop == 1",
    }
    all_slices_passed = True

    for slice_name, query in slices.items():
        slice_idx = X_test.eval(query).to_numpy().nonzero()[0]
        if len(slice_idx) == 0:
            logger.warning(f"Slice '{slice_name}' is empty. Skipping.")
            continue
            
        slice_auc = roc_auc_score(y_test.iloc[slice_idx], model.predict_proba(X_test.iloc[slice_idx])[:, 1])
        logger.info(f"AUC for slice '{slice_name}': {slice_auc:.4f}")
        
        # Check if performance drops significantly on the slice
        if slice_auc < overall_auc * 0.95: # Allow for a 5% drop
            logger.error(f"FAIL: Performance on slice '{slice_name}' is significantly lower than overall performance.")
            all_slices_passed = False
    
    if all_slices_passed:
        logger.info("SUCCESS: All sliced evaluations passed.")
    return all_slices_passed

def run_behavioral_tests(model, X_test: pd.DataFrame) -> bool:
    """Runs behavioral tests like invariance and directional expectations."""
    logger.info("--- Running Behavioral Tests ---")
    all_tests_passed = True
    
    # --- Invariance Test ---
    # Prediction should not change if we alter a non-predictive ID
    test_record = X_test.iloc[[0]].copy()
    original_pred = model.predict_proba(test_record)[:, 1][0]
    
    test_record_modified = test_record.copy()
    # Assuming a feature like 'session_uuid' that shouldn't affect the outcome
    # If not present, we can skip or use another irrelevant feature
    if 'session_uuid' in test_record_modified.columns:
        test_record_modified['session_uuid'] = 12345 
        modified_pred = model.predict_proba(test_record_modified)[:, 1][0]
        if not np.isclose(original_pred, modified_pred):
            logger.error("FAIL: Invariance test failed. Prediction changed with session_uuid.")
            all_tests_passed = False
        else:
            logger.info("SUCCESS: Invariance test passed.")

    # --- Directional Expectation Test ---
    # Adding an 'add_to_cart' event should increase the propensity score
    # Find a record with a moderate number of add_to_cart events
    try:
        record_to_test = X_test[X_test['add_to_cart_count'] > 0].iloc[[0]].copy()
        base_pred = model.predict_proba(record_to_test)[:, 1][0]
        
        record_to_test['add_to_cart_count'] += 1
        higher_pred = model.predict_proba(record_to_test)[:, 1][0]
        
        if higher_pred <= base_pred:
            logger.error("FAIL: Directional test failed. Increasing add_to_cart_count did not increase score.")
            all_tests_passed = False
        else:
            logger.info("SUCCESS: Directional test passed.")
    except IndexError:
        logger.warning("Skipping directional test: no suitable test records found.")

    return all_tests_passed

def advanced_tests(run_id: str, test_data_path: str):
    mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])

    logger.info(f"Running advanced tests for model run: {run_id}")
    model = mlflow.lightgbm.load_model(f"runs:/{run_id}/model")
    
    df_test = pd.read_parquet(test_data_path)
    X_test = df_test.drop("target", axis=1)
    y_test = df_test["target"]

    # Get overall AUC from the MLflow run to use as a baseline
    client = mlflow.tracking.MlflowClient()
    overall_auc = client.get_run(run_id).data.metrics["test_auc"]

    sliced_passed = run_sliced_evaluation(model, X_test, y_test, overall_auc)
    behavioral_passed = run_behavioral_tests(model, X_test)

    if not (sliced_passed and behavioral_passed):
        logger.error("One or more advanced tests failed. Halting promotion.")
        sys.exit(1) # Exit with a non-zero code to fail the Airflow task
    
    logger.info("All advanced tests passed successfully.")
    sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", type=str, required=True)
    parser.add_argument("--test-data-path", type=str, required=True)
    args = parser.parse_args()
    advanced_tests(args.run_id, args.test_data_path)