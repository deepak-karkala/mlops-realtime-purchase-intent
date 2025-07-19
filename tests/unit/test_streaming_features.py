from unittest.mock import MagicMock
import pytest
from datetime import datetime

import sys
sys.path.append('src/feature_engineering')
from streaming_features import update_session_state

@pytest.fixture
def mock_spark_state():
    """Mocks the Spark state object."""
    state_store = {}
    
    mock_state = MagicMock()
    
    def exists_func():
        return bool(state_store)
        
    def get_func():
        return state_store.get('state')

    def update_func(new_state):
        state_store['state'] = new_state

    mock_state.exists = property(fget=exists_func)
    mock_state.get = property(fget=get_func)
    mock_state.update = update_func

    return mock_state

def test_update_session_state_new_session(mock_spark_state):
    """Test the initialization and update of a new session."""
    
    # Mock an incoming event
    MockEvent = type("MockEvent", (), {"product_id": "prodA", "event_type": "page_view"})
    new_events = [MockEvent()]
    
    # Run the function
    results = list(update_session_state("sess1", iter(new_events), mock_spark_state))
    
    # Assert state was updated
    assert mock_spark_state.get['add_to_cart_count'] == 0
    assert "prodA" in mock_spark_state.get['distinct_products_viewed']
    
    # Assert correct output was yielded
    assert len(results) == 1
    assert results[0][2] == 1 # distinct_products_viewed_count

def test_update_session_state_existing_session(mock_spark_state):
    """Test updating an already existing session state."""
    
    # Pre-populate the state
    initial_state = {
        "session_start_time": datetime.utcnow(),
        "distinct_products_viewed": {"prodA"},
        "add_to_cart_count": 0
    }
    mock_spark_state.update(initial_state)

    # Mock a new event
    MockEvent = type("MockEvent", (), {"product_id": "prodB", "event_type": "add_to_cart"})
    new_events = [MockEvent()]

    # Run the function
    results = list(update_session_state("sess1", iter(new_events), mock_spark_state))

    # Assert state was updated correctly
    assert mock_spark_state.get['add_to_cart_count'] == 1
    assert len(mock_spark_state.get['distinct_products_viewed']) == 2