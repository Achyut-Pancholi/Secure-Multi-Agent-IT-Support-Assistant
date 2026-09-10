import sys
from pathlib import Path

# Add project root to sys.path so 'app' package is resolved properly
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import uvicorn
from fastapi import FastAPI
from app.api.routes import router
from app.observability.logging import setup_logging
from app.observability.metrics import metrics_router

def create_app() -> FastAPI:
    # Initialize observability before starting the app
    setup_logging()
    
    app = FastAPI(
        title="Secure Multi-Agent IT Support Assistant",
        description="POC for a secure, multi-agent AI support system.",
        version="0.1.0"
    )
    
    app.include_router(router, prefix="/api/v1")
    app.include_router(metrics_router)
    
    return app

app = create_app()

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8000)

if __name__ == "__main__":
    run_server()

