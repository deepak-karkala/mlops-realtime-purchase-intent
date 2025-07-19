import uuid
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal, Optional

# Defines the rigid schema of an incoming event.
# Pydantic will automatically validate incoming data against this.
class RawClickstreamEvent(BaseModel):
    event_id: str
    event_type: Literal['page_view', 'add_to_cart', 'purchase', 'search']
    product_id: Optional[str]
    user_id: Optional[str]
    session_id: str
    client_timestamp: datetime
    
# Defines the schema for the enriched event we produce.
class ProcessedEvent(RawClickstreamEvent):
    processing_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    server_timestamp: datetime = Field(default_factory=datetime.utcnow)
    # In a real system, we might add geo-location from IP, etc.```
