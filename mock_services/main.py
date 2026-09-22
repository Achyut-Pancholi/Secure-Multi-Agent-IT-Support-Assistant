from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
import uvicorn
import os
import json

app = FastAPI(title="Mock Internal IT Services API")

# Setup Persistence for Tickets
MEMORY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "memory")
os.makedirs(MEMORY_DIR, exist_ok=True)
TICKETS_FILE = os.path.join(MEMORY_DIR, "mock_tickets.json")

# Mock Database
mock_users = {
    "user123": {"department": "Engineering", "vpn_access": True, "finance_access": False},
    "user456": {"department": "Finance", "vpn_access": True, "finance_access": True},
}

mock_services = {
    "vpn": {"status": "degraded", "active_incidents": 1},
    "finance_db": {"status": "operational", "active_incidents": 0},
}

def load_tickets():
    if os.path.exists(TICKETS_FILE):
        with open(TICKETS_FILE, "r") as f:
            try:
                return json.load(f)
            except:
                return []
    return []

def save_tickets(tickets):
    with open(TICKETS_FILE, "w") as f:
        json.dump(tickets, f, indent=2)

mock_tickets = load_tickets()

class TicketRequest(BaseModel):
    user_id: str
    description: str
    category: str
    priority: str

class TicketUpdate(BaseModel):
    description: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None

def verify_token(authorization: str):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization.replace("Bearer ", "")
    if token != "mock-internal-token-secret":
        raise HTTPException(status_code=403, detail="Forbidden")

@app.get("/internal/users/{user_id}/access")
async def get_user_access(user_id: str, authorization: Optional[str] = Header(None)):
    verify_token(authorization)
    if user_id not in mock_users:
        raise HTTPException(status_code=404, detail="User not found")
    return mock_users[user_id]

@app.get("/internal/services/{service_name}/status")
async def get_service_status(service_name: str, authorization: Optional[str] = Header(None)):
    verify_token(authorization)
    if service_name not in mock_services:
        raise HTTPException(status_code=404, detail="Service not found")
    return mock_services[service_name]

@app.post("/internal/tickets", status_code=201)
async def create_ticket(ticket: TicketRequest, authorization: Optional[str] = Header(None)):
    verify_token(authorization)
    ticket_id = f"TKT-{len(mock_tickets) + 1000}"
    new_ticket = {
        "id": ticket_id,
        **ticket.model_dump(),
        "status": "open"
    }
    mock_tickets.append(new_ticket)
    save_tickets(mock_tickets)
    return {"ticket_id": ticket_id, "status": "created", "ticket": new_ticket}

@app.put("/internal/tickets/{ticket_id}")
async def update_ticket(ticket_id: str, updates: TicketUpdate, authorization: Optional[str] = Header(None)):
    verify_token(authorization)
    for i, t in enumerate(mock_tickets):
        if t["id"] == ticket_id:
            update_data = updates.model_dump(exclude_unset=True)
            mock_tickets[i].update(update_data)
            save_tickets(mock_tickets)
            return {"status": "updated", "ticket": mock_tickets[i]}
    raise HTTPException(status_code=404, detail="Ticket not found")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)

