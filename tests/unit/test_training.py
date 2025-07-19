import os
from unittest.mock import patch, MagicMock
import pytest
import pandas as pd

import sys
sys.path.append('src/model_training')
import train

@pytest.fixture
def mock_train_data():
    """Create a mock DataFrame for testing."""
    return pd.DataFrame({
        'feature1': range(100),
        'feature2': [i * 0.1 for i in range(100)],
        'target': [0] * 50 + [1] * 50
    })

@patch('train.mlflow')
@patch('train.lgb.LGBMClassifier')
@patch('pandas.read_parquet')
def test_main_training_logic(mock_read_parquet, mock_lgbm, mock_mlflow, mock_train_data):
    """Test the main training function's flow."""
    # Setup mocks
    mock_read_parquet.return_value = mock_train_data
    mock_lgbm_instance = MagicMock()
    mock_lgbm.return_value = mock_lgbm_instance
    os.environ['MLFLOW_TRACKING_URI'] = 'http://dummy-uri'
    os.environ['SM_CHANNEL_TRAIN'] = '/data'

    # Run the main function
    train.main()
    
    # Assertions
    mock_mlflow.set_experiment.assert_called_with("purchase-intent-training")
    mock_mlflow.start_run.assert_called_once()
    mock_lgbm_instance.fit.assert_called_once()
    mock_mlflow.log_params.assert_called()
    mock_mlflow.log_metric.assert_called_with("validation_auc", pytest.approx(0.693, 0.1)) # Check for some value
    mock_mlflow.lightgbm.log_model.assert_called_once()