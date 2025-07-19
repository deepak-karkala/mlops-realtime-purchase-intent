import os
import argparse
import logging
import pandas as pd
import lightgbm as lgb
import mlflow
from sklearn.model_selection import train_test_split

logging.basicConfig(level=logging.INFO, format="%(asctime)-15s %(message)s")
logger = logging.getLogger()

def main():
    # --- MLflow setup ---
    # The MLFLOW_TRACKING_URI is set by the SageMaker operator in Airflow
    mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
    mlflow.set_experiment("purchase-intent-training")

    # --- Parse arguments ---
    # SageMaker passes hyperparameters and data paths as command-line arguments.
    parser = argparse.ArgumentParser()
    parser.add_argument("--n_estimators", type=int, default=200)
    parser.add_argument("--learning_rate", type=float, default=0.1)
    # SageMaker environment variables for data channels
    parser.add_argument("--train", type=str, default=os.environ.get("SM_CHANNEL_TRAIN"))
    args = parser.parse_args()

    # --- Data Loading ---
    logger.info("Loading training data...")
    df = pd.read_parquet(args.train)
    X = df.drop("target", axis=1)
    y = df["target"]
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

    # --- MLflow Tracking ---
    with mlflow.start_run() as run:
        run_id = run.info.run_id
        logger.info(f"Started MLflow Run: {run_id}")
        mlflow.log_params(vars(args))

        # --- Model Training ---
        logger.info("Training LightGBM model...")
        model = lgb.LGBMClassifier(
            n_estimators=args.n_estimators,
            learning_rate=args.learning_rate,
            objective='binary'
        )
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            callbacks=[lgb.early_stopping(10, verbose=False), lgb.log_evaluation(period=0)]
        )

        # --- Log artifacts & metrics ---
        val_auc = model.best_score_['valid_0']['binary_logloss'] # Example metric
        mlflow.log_metric("validation_auc", val_auc)
        mlflow.lightgbm.log_model(model, "model")
        logger.info(f"Logged model with Validation AUC: {val_auc}")

if __name__ == "__main__":
    main()