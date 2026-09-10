from pydantic import BaseModel
from typing import Optional, List, Dict

class SupportRequestSchema(BaseModel):
    user_id: str
    query: str
    history: Optional[List[Dict[str, str]]] = None
    
class SupportResponseSchema(BaseModel):
    request_id: str
    response: str
    status: str
