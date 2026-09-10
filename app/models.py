from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from enum import Enum

class Priority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class Route(str, Enum):
    KNOWLEDGE = "KNOWLEDGE"
    ACTION = "ACTION"
    UNKNOWN = "UNKNOWN"

class SupportRequest(BaseModel):
    request_id: str
    user_id: str
    query: str

class TriageResult(BaseModel):
    category: str
    priority: Priority
    route: Route
    reason: str

class SupportResponse(BaseModel):
    request_id: str
    response: str
    status: str = "completed"
    
class ErrorResponse(BaseModel):
    request_id: Optional[str] = None
    error: str
    status: str = "error"

