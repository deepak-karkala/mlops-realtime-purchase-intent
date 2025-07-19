import os
import logging
import pandas as pd
import lightgbm as lgb
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from feast import FeatureStore

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- FastAPI App Initialization ---
app = FastAPI()

# --- Model & Feature Store Loading ---
# This happens once at container startup
try:
    MODEL_PATH = "/opt/ml/model/model.joblib" # SageMaker's default model path
    model = pd.read_pickle(MODEL_PATH)
    logger.info("Successfully loaded model from %s", MODEL_PATH)
    
    # Initialize Feast feature store. Assumes feature_repo is packaged with the app.
    # The registry.db path needs to be accessible. For production, a shared path is better.
    fs = FeatureStore(repo_path=".") 
    logger.info("Successfully initialized Feast Feature Store.")
except Exception as e:
    logger.critical("Failed to load model or feature store: %s", e)
    model = None
    fs = None

# --- Pydantic Schemas for Request & Response ---
class PredictionRequest(BaseModel):
    user_id: str
    session_id: str

class PredictionResponse(BaseModel):
    propensity: float
    model_version: str = os.environ.get("MODEL_VERSION", "v0.0.0")
    variant_name: str = os.environ.get("SAGEMAKER_VARIANT_NAME", "unknown")

# --- API Endpoints ---
@app.get("/health")
async def health_check():
    """Health check endpoint for SageMaker to ping."""
    if model is None or fs is None:
        raise HTTPException(status_code=503, detail="Model or Feature Store not loaded")
    return {"status": "ok"}

@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """Main prediction endpoint."""
    if model is None or fs is None:
        raise HTTPException(status_code=503, detail="Model is not ready")

    try:
        # 1. Fetch online features from Feast (Redis)
        feature_vector = fs.get_online_features(
            features=[
                "user_historical_features:lifetime_purchase_count",
                "user_historical_features:avg_order_value_90d",
                "session_streaming_features:add_to_cart_count",
                # ... add all other features here
            ],
            entity_rows=[{"user_id": request.user_id, "session_id": request.session_id}],
        ).to_df()
        
        # 2. Prepare features for the model (drop IDs, ensure order)
        feature_df = feature_vector.drop(columns=["user_id", "session_id", "event_timestamp"])

        # 3. Get prediction
        prediction = model.predict_proba(feature_df)[:, 1][0]
        
        logger.info("Prediction successful for session %s", request.session_id)
        
        # 4. Return response
        return PredictionResponse(propensity=prediction)

    except Exception as e:
        logger.error("Error during prediction: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error during prediction.")