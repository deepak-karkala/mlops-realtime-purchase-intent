import os
import argparse
import logging
import pandas as pd
import mlflow
from sklearn.metrics import roc_auc_score

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)-15s %(message)s")
logger = logging.getLogger()

# A minimum threshold of improvement to prevent deploying models that are only marginally better
MINIMUM_AUC_IMPROVEMENT = 0.005

def evaluate_model(run_id: str, model_name: str, test_data_path: str):
    """
    Evaluates a new model from an MLflow run and compares its performance
    against the current production model.
    
    Args:
        run_id (str): The MLflow run ID of the new model candidate.
        model_name (str): The name of the model in the MLflow Model Registry.
        test_data_path (str): Path to the test dataset.
    """
    mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
    client = mlflow.tracking.MlflowClient()

    # --- 1. Load new model and test data ---
    logger.info(f"Loading new model from run: {run_id}")
    new_model_uri = f"runs:/{run_id}/model"
    new_model = mlflow.lightgbm.load_model(new_model_uri)
    
    df_test = pd.read_parquet(test_data_path)
    X_test = df_test.drop("target", axis=1)
    y_test = df_test["target"]

    # --- 2. Evaluate the new model ---
    logger.info("Evaluating new model on the test set.")
    new_model_preds = new_model.predict_proba(X_test)[:, 1]
    new_model_auc = roc_auc_score(y_test, new_model_preds)
    logger.info(f"New model AUC: {new_model_auc:.4f}")
    
    # Log the test AUC to the new model's run for full traceability
    client.log_metric(run_id, "test_auc", new_model_auc)

    # --- 3. Get the current production model ---
    try:
        prod_versions = client.get_latest_versions(name=model_name, stages=["Production"])
        if not prod_versions:
            logger.info("No production model found. Promoting new model as the first version.")
            return {"is_better": True, "new_model_auc": new_model_auc, "prod_model_auc": -1.0}
        
        prod_model_run_id = prod_versions[0].run_id
        prod_model_metrics = client.get_run(prod_model_run_id).data.metrics
        prod_model_auc = prod_model_metrics.get("test_auc", -1.0)
        logger.info(f"Current production model (run_id: {prod_model_run_id}) has test AUC: {prod_model_auc:.4f}")
        
    except mlflow.exceptions.RestException:
        logger.info(f"Model '{model_name}' not found in registry. Promoting new model as the first version.")
        return {"is_better": True, "new_model_auc": new_model_auc, "prod_model_auc": -1.0}

    # --- 4. Compare and make a decision ---
    is_better = new_model_auc > prod_model_auc + MINIMUM_AUC_IMPROVEMENT
    if is_better:
        logger.info(f"New model is better than production by {new_model_auc - prod_model_auc:.4f}. Proceeding to advanced tests.")
    else:
        logger.info("New model is not significantly better than production. Halting promotion.")

    # This return value will be pushed to Airflow XComs
    return {"is_better": is_better, "new_model_auc": new_model_auc, "prod_model_auc": prod_model_auc}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", type=str, required=True)
    parser.add_argument("--model-name", type=str, required=True)
    parser.add_argument("--test-data-path", type=str, required=True)
    args = parser.parse_args()

    # In Airflow, this function would be called by a PythonOperator,
    # which would then push the return dictionary to XComs.
    evaluate_model(args.run_id, args.model_name, args.test_data_path)