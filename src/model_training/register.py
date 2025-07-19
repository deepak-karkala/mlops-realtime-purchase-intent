import os
import argparse
import logging
import mlflow

logging.basicConfig(level=logging.INFO, format="%(asctime)-15s %(message)s")
logger = logging.getLogger()

def register_model(run_id: str, model_name: str):
    """
    Registers a new model version from an MLflow run and transitions it to Staging.
    
    Args:
        run_id (str): The MLflow run ID of the model to register.
        model_name (str): The name of the model in the MLflow Model Registry.
    """
    mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
    client = mlflow.tracking.MlflowClient()

    model_uri = f"runs:/{run_id}/model"
    logger.info(f"Registering model '{model_name}' from URI: {model_uri}")

    # Register the model, which creates a new version
    model_version_info = mlflow.register_model(model_uri, model_name)
    version = model_version_info.version
    logger.info(f"Successfully registered model version: {version}")

    # Add a description to the model version
    description = (
        f"This model (version {version}) was automatically promoted by the "
        f"training pipeline on {datetime.date.today()}. "
        f"Source run ID: {run_id}"
    )
    client.update_model_version(
        name=model_name,
        version=version,
        description=description
    )

    # Transition the new model version to the "Staging" stage
    logger.info(f"Transitioning model version {version} to 'Staging'...")
    client.transition_model_version_stage(
        name=model_name,
        version=version,
        stage="Staging",
        archive_existing_versions=True # Crucial for production!
    )
    logger.info("Transition to Staging complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", type=str, required=True)
    parser.add_argument("--model-name", type=str, required=True)
    args = parser.parse_args()
    register_model(args.run_id, args.model_name)