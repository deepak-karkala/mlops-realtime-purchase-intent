from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import pandas as pd
import pytest

# Add src to path to allow imports
import sys
sys.path.append('src/serving')
from app import app

client = TestClient(app)

@patch('app.fs') # Mock the Feast FeatureStore object
def test_predict_success(mock_fs):
    """Test the happy path for the /predict endpoint."""
    # Mock the return value of get_online_features
    mock_feature_df = pd.DataFrame({
        "user_id": ["user123"],
        "session_id": ["sess456"],
        "lifetime_purchase_count": [5],
        "avg_order_value_90d": [99.5],
        "add_to_cart_count": [2],
        "event_timestamp": [pd.Timestamp.now()]
    })
    mock_fs.get_online_features.return_value.to_df.return_value = mock_feature_df

    # Mock the model object
    with patch('app.model') as mock_model:
        mock_model.predict_proba.return_value = [[0.2, 0.8]] # Mock output
        
        response = client.post(
            "/predict",
            json={"user_id": "user123", "session_id": "sess456"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "propensity" in data
        assert 0.0 <= data["propensity"] <= 1.0
        assert data["propensity"] == 0.8

def test_health_check():
    """Test the /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}